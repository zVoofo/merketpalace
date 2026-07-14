from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Count
from orders.models import OrderItem
from catalog.models import Category, Brand, SearchQuery, SearchRequest
from .models import Listing, ModerationQueue, Review
from .forms import ListingForm, ReviewForm, validate_media_files
from .services import save_listing_media, user_can_review, update_listing_rating, remoderate_listing
from .moderation import schedule_auto_moderation


def listing_detail(request, slug):
    listing = get_object_or_404(
        Listing.objects.select_related('category', 'brand', 'user').prefetch_related('images'),
        slug=slug, status=Listing.Status.ACTIVE
    )
    listing.views_count += 1
    listing.save(update_fields=['views_count'])
    similar = Listing.objects.filter(
        category=listing.category, status=Listing.Status.ACTIVE
    ).exclude(pk=listing.pk).prefetch_related('images')[:6]
    reviews = listing.reviews.filter(status=Review.Status.APPROVED).select_related('reviewer')
    can_review = False
    review_block_reason = ''
    review_form = None
    if request.user.is_authenticated:
        can_review, review_block_reason = user_can_review(request.user, listing)
        if can_review:
            review_form = ReviewForm()
    return render(request, 'listings/show.html', {
        'title': listing.title,
        'listing': listing,
        'similar': similar,
        'reviews': reviews,
        'review_form': review_form,
        'can_review': can_review,
        'review_block_reason': review_block_reason,
    })


@login_required
def listing_create(request):
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES)
        media_files = request.FILES.getlist('media')
        media_errors = validate_media_files(media_files, require_min=True)
        if form.is_valid() and not media_errors:
            listing = form.save(commit=False)
            listing.user = request.user
            listing.status = Listing.Status.PENDING
            if request.user.active_role != 'seller':
                request.user.active_role = 'seller'
                request.user.save(update_fields=['active_role'])
            listing.save()
            save_listing_media(listing, media_files)
            ModerationQueue.objects.create(listing=listing, reason='Новое объявление')
            schedule_auto_moderation(listing.pk)
            messages.success(
                request,
                'Объявление создано. Автоматическая проверка займёт около 30 секунд — затем оно появится в каталоге.',
            )
            return redirect('seller:listings')
        for err in media_errors:
            messages.error(request, err)
        for field, errors in form.errors.items():
            for err in errors:
                messages.error(request, f'{field}: {err}')
    else:
        form = ListingForm()
    return render(request, 'listings/create.html', {
        'title': 'Создать объявление',
        'form': form,
        'categories': Category.objects.filter(is_active=True),
        'brands': Brand.objects.filter(is_active=True),
    })


@login_required
def listing_edit(request, pk):
    listing = get_object_or_404(Listing, pk=pk, user=request.user)
    if request.method == 'POST':
        remove_ids = [x for x in request.POST.getlist('remove_media') if x.isdigit()]

        form = ListingForm(request.POST, request.FILES, instance=listing)
        media_files = request.FILES.getlist('media')
        remaining = listing.images.count()
        if remove_ids:
            remaining = listing.images.exclude(pk__in=remove_ids).count()
        media_errors = validate_media_files(
            media_files, existing_count=remaining, require_min=False,
        )
        if remaining == 0 and not media_files:
            media_errors.append('Добавьте хотя бы 1 фото или видео')
        if form.is_valid() and not media_errors:
            if remove_ids:
                listing.images.filter(pk__in=remove_ids).delete()
            listing = form.save()
            if media_files:
                save_listing_media(listing, media_files)
            remoderate_listing(listing)
            messages.success(request, 'Объявление обновлено и отправлено на проверку (~30 сек)')
            return redirect('seller:listings')
        for err in media_errors:
            messages.error(request, err)
    else:
        form = ListingForm(instance=listing)
    last_reject = ModerationQueue.objects.filter(
        listing=listing, status='rejected',
    ).order_by('-created_at').first()
    return render(request, 'listings/edit.html', {
        'title': 'Редактировать',
        'form': form,
        'listing': listing,
        'last_reject': last_reject,
    })


@login_required
def review_create(request, slug):
    listing = get_object_or_404(Listing, slug=slug, status=Listing.Status.ACTIVE)
    can_review, reason = user_can_review(request.user, listing)
    if not can_review:
        messages.error(request, reason)
        return redirect('listings:detail', slug=slug)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.listing = listing
            review.reviewer = request.user
            review.seller = listing.user
            review.status = Review.Status.APPROVED
            review.save()
            update_listing_rating(listing)
            messages.success(request, 'Спасибо за отзыв!')
    return redirect('listings:detail', slug=slug)


@login_required
def seller_dashboard(request):
    listings = Listing.objects.filter(user=request.user)
    orders_count = request.user.sales_received.count() if hasattr(request.user, 'sales_received') else 0
    failed = SearchQuery.objects.filter(results_count=0).values('query').annotate(
        cnt=Count('id')
    ).order_by('-cnt')[:10]
    my_looking = SearchRequest.objects.filter(user=request.user).order_by('-created_at')[:5]
    return render(request, 'seller/dashboard.html', {
        'title': 'Кабинет продавца',
        'listings_count': listings.count(),
        'active_count': listings.filter(status=Listing.Status.ACTIVE).count(),
        'total_views': sum(l.views_count for l in listings),
        'failed_searches': failed,
        'orders_count': orders_count,
        'my_looking': my_looking,
    })


@login_required
@require_POST
def listing_unpublish(request, pk):
    listing = get_object_or_404(Listing, pk=pk, user=request.user)
    if listing.status == Listing.Status.ARCHIVED:
        messages.info(request, 'Объявление уже снято с публикации')
    else:
        listing.status = Listing.Status.ARCHIVED
        listing.save(update_fields=['status'])
        messages.success(request, 'Объявление снято с публикации')
    return redirect('seller:listings')


@login_required
@require_POST
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, user=request.user)
    if OrderItem.objects.filter(listing=listing).exists():
        messages.error(request, 'Нельзя удалить: по этому объявлению есть заказы. Снимите с публикации.')
        return redirect('seller:listings')
    listing.delete()
    messages.success(request, 'Объявление удалено')
    return redirect('seller:listings')


@login_required
def seller_listings(request):
    listings = Listing.objects.filter(user=request.user).prefetch_related('images')
    rejection_reasons = {}
    for mq in ModerationQueue.objects.filter(
        listing__user=request.user, status='rejected',
    ).select_related('listing').order_by('-created_at'):
        if mq.listing_id not in rejection_reasons:
            rejection_reasons[mq.listing_id] = mq.reason
    return render(request, 'seller/listings.html', {
        'title': 'Мои объявления',
        'listings': listings,
        'rejection_reasons': rejection_reasons,
    })
