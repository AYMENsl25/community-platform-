/* eslint-disable */
// Generated from FastAPI OpenAPI. Do not edit by hand.

export type components = {
  schemas: {
    "CategoryResponse": {
    "id": string
    "name": string
    "slug": string
    "description"?: string | null
  }
    "ClubCard": {
    "id": string
    "name": string
    "slug": string
    "description"?: string | null
    "logo_url"?: string | null
    "cover_image_url"?: string | null
    "city"?: string | null
    "country"?: string | null
    "member_count": number
    "category_name"?: string | null
  }
    "ClubCreate": {
    "name": string
    "slug"?: string | null
    "description"?: string | null
    "category_id"?: string | null
    "logo_url"?: string | null
    "cover_image_url"?: string | null
    "city"?: string | null
    "country"?: string | null
    "visibility"?: string
    "status"?: string
  }
    "ClubDeletionState": {
    "club_id": string
    "deleted": boolean
  }
    "ClubDetail": {
    "id": string
    "name": string
    "slug": string
    "description"?: string | null
    "logo_url"?: string | null
    "cover_image_url"?: string | null
    "city"?: string | null
    "country"?: string | null
    "member_count": number
    "category_name"?: string | null
    "owner_id": string
    "category_id"?: string | null
    "visibility": string
    "status": string
    "owner_name": string
    "owner_avatar_url"?: string | null
  }
    "ClubEventSummary": {
    "id": string
    "title": string
    "slug": string
    "event_type": string
    "starts_at": string
    "ends_at"?: string | null
    "city"?: string | null
    "registered_count": number
    "waitlist_count": number
    "price_amount": string
    "currency": string
    "cover_image_url"?: string | null
  }
    "ClubMemberPreview": {
    "user_id": string
    "display_name": string
    "avatar_url"?: string | null
    "role": string
    "joined_at": string
  }
    "ClubMembershipState": {
    "id": string
    "club_id": string
    "user_id": string
    "role": string
    "status": string
    "joined_at": string
    "left_at"?: string | null
  }
    "ClubUpdate": {
    "name"?: string | null
    "slug"?: string | null
    "description"?: string | null
    "category_id"?: string | null
    "logo_url"?: string | null
    "cover_image_url"?: string | null
    "city"?: string | null
    "country"?: string | null
    "visibility"?: string | null
    "status"?: string | null
  }
    "ClubViewerState": {
    "club_id": string
    "is_member": boolean
    "member_role"?: string | null
    "member_status"?: string | null
    "joined_at"?: string | null
  }
    "CurrentUserProfile": {
    "id": string
    "clerk_user_id": string
    "email": string
    "display_name"?: string | null
    "avatar_url"?: string | null
    "platform_role": string
  }
    "EventCapacity": {
    "event_id": string
    "capacity"?: number | null
    "registered_count": number
    "waitlist_count": number
    "spots_left"?: number | null
    "is_full": boolean
  }
    "EventCard": {
    "id": string
    "club_id": string
    "club_name": string
    "title": string
    "slug": string
    "description"?: string | null
    "event_type": string
    "starts_at": string
    "ends_at"?: string | null
    "city"?: string | null
    "country"?: string | null
    "location_name"?: string | null
    "capacity"?: number | null
    "registered_count": number
    "waitlist_count": number
    "price_amount": string
    "currency": string
    "cover_image_url"?: string | null
    "category_name"?: string | null
  }
    "EventCheckoutRequest": {
    "return_path"?: string | null
    "idempotency_key"?: string | null
  }
    "EventCheckoutSession": {
    "event_id": string
    "provider": string
    "checkout_id"?: string | null
    "checkout_url"?: string | null
    "amount": string
    "currency": string
    "status": string
    "mode": string
    "message"?: string | null
  }
    "EventCreate": {
    "club_id": string
    "title": string
    "slug"?: string | null
    "description"?: string | null
    "event_type"?: string
    "starts_at": string
    "ends_at"?: string | null
    "timezone"?: string
    "location_name"?: string | null
    "address"?: string | null
    "city"?: string | null
    "country"?: string | null
    "lat"?: number | string | null
    "lng"?: number | string | null
    "capacity"?: number | null
    "price_amount"?: number | string
    "currency"?: string
    "status"?: string
    "requires_approval"?: boolean
    "cover_image_url"?: string | null
  }
    "EventDeletionState": {
    "event_id": string
    "deleted": boolean
  }
    "EventDetail": {
    "id": string
    "club_id": string
    "club_name": string
    "title": string
    "slug": string
    "description"?: string | null
    "event_type": string
    "starts_at": string
    "ends_at"?: string | null
    "city"?: string | null
    "country"?: string | null
    "location_name"?: string | null
    "capacity"?: number | null
    "registered_count": number
    "waitlist_count": number
    "price_amount": string
    "currency": string
    "cover_image_url"?: string | null
    "category_name"?: string | null
    "created_by": string
    "timezone": string
    "address"?: string | null
    "lat"?: string | null
    "lng"?: string | null
    "status": string
    "requires_approval": boolean
    "club_slug": string
    "club_logo_url"?: string | null
    "organizer_name": string
    "organizer_avatar_url"?: string | null
    "is_full": boolean
  }
    "EventRegistrationAttendee": {
    "registration_id": string
    "event_id": string
    "user_id": string
    "display_name": string
    "email": string
    "avatar_url"?: string | null
    "registration_status": string
    "payment_required"?: boolean
    "payment_status"?: string
    "payment_id"?: string | null
    "amount"?: string | null
    "currency"?: string | null
    "registered_at": string
    "confirmed_at"?: string | null
  }
    "EventRegistrationState": {
    "id": string
    "event_id": string
    "user_id": string
    "status": string
    "payment_required"?: boolean
    "payment_status"?: string
    "payment_id"?: string | null
    "checkout_id"?: string | null
    "idempotency_key"?: string | null
    "waitlist_position"?: number | null
    "note"?: string | null
    "registered_at": string
    "confirmed_at"?: string | null
    "cancelled_at"?: string | null
  }
    "EventUpdate": {
    "title"?: string | null
    "slug"?: string | null
    "description"?: string | null
    "event_type"?: string | null
    "starts_at"?: string | null
    "ends_at"?: string | null
    "timezone"?: string | null
    "location_name"?: string | null
    "address"?: string | null
    "city"?: string | null
    "country"?: string | null
    "lat"?: number | string | null
    "lng"?: number | string | null
    "capacity"?: number | null
    "price_amount"?: number | string | null
    "currency"?: string | null
    "status"?: string | null
    "requires_approval"?: boolean | null
    "cover_image_url"?: string | null
  }
    "HTTPValidationError": {
    "detail"?: Array<components["schemas"]["ValidationError"]>
  }
    "MoyasarWebhookPayload": {
    "id": string
    "type": string
    "created_at"?: string | null
    "secret_token"?: string | null
    "account_name"?: string | null
    "live"?: boolean | null
    "data": Record<string, unknown>
  }
    "MoyasarWebhookResult": {
    "received": boolean
    "event_type": string
    "processed": boolean
    "payment_id"?: string | null
    "registration_status"?: string | null
    "message"?: string | null
  }
    "MyClubSummary": {
    "id": string
    "name": string
    "slug": string
    "description"?: string | null
    "logo_url"?: string | null
    "cover_image_url"?: string | null
    "city"?: string | null
    "country"?: string | null
    "member_count": number
    "category_name"?: string | null
    "visibility": string
    "status": string
    "member_role": string
    "member_status": string
  }
    "MyEventSummary": {
    "id": string
    "club_id": string
    "club_name": string
    "title": string
    "slug": string
    "event_type": string
    "starts_at": string
    "ends_at"?: string | null
    "city"?: string | null
    "status": string
    "capacity"?: number | null
    "registered_count": number
    "waitlist_count": number
    "price_amount": string
    "currency": string
    "cover_image_url"?: string | null
  }
    "MyNotificationSummary": {
    "id": string
    "kind": string
    "title": string
    "body": string
    "entity_type"?: string | null
    "entity_id"?: string | null
    "read_at"?: string | null
    "created_at": string
    "is_read": boolean
  }
    "MyPreferences": {
    "interest_categories": Array<string>
    "interest_tags": Array<string>
    "preferred_city"?: string | null
    "max_distance_km"?: number | null
    "notify_email": boolean
    "notify_push": boolean
  }
    "MyPreferencesUpdate": {
    "interest_categories"?: Array<string> | null
    "interest_tags"?: Array<string> | null
    "preferred_city"?: string | null
    "max_distance_km"?: number | null
    "notify_email"?: boolean | null
    "notify_push"?: boolean | null
  }
    "MyProfile": {
    "id": string
    "clerk_user_id": string
    "email": string
    "username"?: string | null
    "display_name": string
    "avatar_url"?: string | null
    "bio"?: string | null
    "city"?: string | null
    "country"?: string | null
    "platform_role": string
    "is_onboarded": boolean
  }
    "MyProfileUpdate": {
    "username"?: string | null
    "display_name"?: string | null
    "avatar_url"?: string | null
    "bio"?: string | null
    "city"?: string | null
    "country"?: string | null
    "is_onboarded"?: boolean | null
  }
    "MyRegistrationSummary": {
    "event_id": string
    "club_id": string
    "club_name": string
    "title": string
    "slug": string
    "event_type": string
    "starts_at": string
    "registration_status": string
    "payment_required"?: boolean
    "payment_status"?: string
    "payment_id"?: string | null
    "price_amount": string
    "currency": string
    "registered_at": string
    "city"?: string | null
    "cover_image_url"?: string | null
  }
    "MySavedEventSummary": {
    "event_id": string
    "club_id": string
    "club_name": string
    "title": string
    "slug": string
    "event_type": string
    "starts_at": string
    "city"?: string | null
    "saved_at": string
    "cover_image_url"?: string | null
  }
    "NotificationReadState": {
    "id": string
    "read_at": string
  }
    "NotificationsReadAllState": {
    "updated_count": number
  }
    "OrganizerRequestCreate": {
    "reason"?: string | null
  }
    "OrganizerRequestReview": {
    "admin_note"?: string | null
  }
    "OrganizerRequestState": {
    "id": string
    "user_id": string
    "user_email": string
    "user_display_name": string
    "status": string
    "reason"?: string | null
    "admin_note"?: string | null
    "reviewed_by"?: string | null
    "reviewed_at"?: string | null
    "created_at": string
    "updated_at": string
  }
    "PaymentAdminActionResult": {
    "action_id": string
    "payment_id": string
    "action_type": string
    "status": string
    "payment_status": string
    "registration_payment_status"?: string | null
    "message": string
  }
    "PaymentAdminRecord": {
    "id": string
    "event_id": string
    "event_title": string
    "user_id": string
    "user_email": string
    "provider": string
    "provider_payment_id": string
    "provider_invoice_id"?: string | null
    "amount": string
    "currency": string
    "status": string
    "paid_at"?: string | null
    "created_at": string
    "updated_at": string
    "registration_status"?: string | null
    "registration_payment_status"?: string | null
  }
    "PaymentDisputeRequest": {
    "reason": string
    "notes"?: string | null
    "provider_reference"?: string | null
  }
    "PaymentRefundRequest": {
    "amount"?: number | string | null
    "reason"?: string | null
    "notes"?: string | null
    "provider_reference"?: string | null
  }
    "RecommendationEventCreate": {
    "event_id": string
    "source"?: string
    "score"?: number | string | null
    "action"?: string
  }
    "RecommendationEventState": {
    "id": string
    "user_id": string
    "event_id": string
    "source": string
    "score"?: string | null
    "action": string
    "created_at": string
  }
    "SavedEventState": {
    "user_id": string
    "event_id": string
    "saved": boolean
    "created_at"?: string | null
  }
    "SearchResult": {
    "entity_type": string
    "entity_id": string
    "title": string
    "body"?: string | null
    "city"?: string | null
    "country"?: string | null
    "created_at": string
    "rank": number
  }
    "TagResponse": {
    "id": string
    "name": string
    "slug": string
  }
    "ValidationError": {
    "loc": Array<string | number>
    "msg": string
    "type": string
  }
  }
}

export type paths = {
  "/api/v1/health/db": {
    get: {
      response: Record<string, string>
    }
  }
  "/api/v1/metrics": {
    get: {
      response: Record<string, unknown>
    }
  }
  "/api/v1/meta/categories": {
    get: {
      response: Array<components["schemas"]["CategoryResponse"]>
    }
  }
  "/api/v1/meta/tags": {
    get: {
      response: Array<components["schemas"]["TagResponse"]>
    }
  }
  "/api/v1/auth/me": {
    get: {
      response: components["schemas"]["CurrentUserProfile"]
    }
  }
  "/api/v1/me/profile": {
    get: {
      response: components["schemas"]["MyProfile"]
    }
    patch: {
      response: components["schemas"]["MyProfile"]
      body: components["schemas"]["MyProfileUpdate"]
    }
  }
  "/api/v1/me/preferences": {
    get: {
      response: components["schemas"]["MyPreferences"]
    }
    patch: {
      response: components["schemas"]["MyPreferences"]
      body: components["schemas"]["MyPreferencesUpdate"]
    }
  }
  "/api/v1/me/clubs": {
    get: {
      response: Array<components["schemas"]["MyClubSummary"]>
    }
  }
  "/api/v1/me/events": {
    get: {
      response: Array<components["schemas"]["MyEventSummary"]>
    }
  }
  "/api/v1/me/registrations": {
    get: {
      response: Array<components["schemas"]["MyRegistrationSummary"]>
    }
  }
  "/api/v1/me/saved-events": {
    get: {
      response: Array<components["schemas"]["MySavedEventSummary"]>
    }
  }
  "/api/v1/me/notifications": {
    get: {
      response: Array<components["schemas"]["MyNotificationSummary"]>
    }
  }
  "/api/v1/me/notifications/read-all": {
    patch: {
      response: components["schemas"]["NotificationsReadAllState"]
    }
  }
  "/api/v1/me/notifications/{notification_id}/read": {
    patch: {
      response: components["schemas"]["NotificationReadState"]
    }
  }
  "/api/v1/me/organizer-request": {
    get: {
      response: components["schemas"]["OrganizerRequestState"] | null
    }
    post: {
      response: components["schemas"]["OrganizerRequestState"]
      body: components["schemas"]["OrganizerRequestCreate"]
    }
  }
  "/api/v1/admin/organizer-requests": {
    get: {
      response: Array<components["schemas"]["OrganizerRequestState"]>
    }
  }
  "/api/v1/admin/organizer-requests/{request_id}/approve": {
    post: {
      response: components["schemas"]["OrganizerRequestState"]
      body: components["schemas"]["OrganizerRequestReview"]
    }
  }
  "/api/v1/admin/organizer-requests/{request_id}/reject": {
    post: {
      response: components["schemas"]["OrganizerRequestState"]
      body: components["schemas"]["OrganizerRequestReview"]
    }
  }
  "/api/v1/clubs": {
    get: {
      response: Array<components["schemas"]["ClubCard"]>
    }
    post: {
      response: components["schemas"]["ClubDetail"]
      body: components["schemas"]["ClubCreate"]
    }
  }
  "/api/v1/clubs/{club_id}": {
    patch: {
      response: components["schemas"]["ClubDetail"]
      body: components["schemas"]["ClubUpdate"]
    }
    delete: {
      response: components["schemas"]["ClubDeletionState"]
    }
  }
  "/api/v1/clubs/{club_id}/join": {
    post: {
      response: components["schemas"]["ClubMembershipState"]
    }
  }
  "/api/v1/clubs/{club_id}/leave": {
    post: {
      response: components["schemas"]["ClubMembershipState"]
    }
  }
  "/api/v1/clubs/{club_id}/members": {
    get: {
      response: Array<components["schemas"]["ClubMemberPreview"]>
    }
  }
  "/api/v1/clubs/{club_id}/events": {
    get: {
      response: Array<components["schemas"]["ClubEventSummary"]>
    }
  }
  "/api/v1/clubs/{club_id}/membership": {
    get: {
      response: components["schemas"]["ClubViewerState"]
    }
  }
  "/api/v1/clubs/{slug}": {
    get: {
      response: components["schemas"]["ClubDetail"]
    }
  }
  "/api/v1/events": {
    get: {
      response: Array<components["schemas"]["EventCard"]>
    }
    post: {
      response: components["schemas"]["EventDetail"]
      body: components["schemas"]["EventCreate"]
    }
  }
  "/api/v1/events/{event_id}": {
    get: {
      response: components["schemas"]["EventDetail"]
    }
    patch: {
      response: components["schemas"]["EventDetail"]
      body: components["schemas"]["EventUpdate"]
    }
    delete: {
      response: components["schemas"]["EventDeletionState"]
    }
  }
  "/api/v1/events/{event_id}/registrations": {
    get: {
      response: Array<components["schemas"]["EventRegistrationAttendee"]>
    }
  }
  "/api/v1/events/{event_id}/capacity": {
    get: {
      response: components["schemas"]["EventCapacity"]
    }
  }
  "/api/v1/events/{event_id}/register": {
    post: {
      response: components["schemas"]["EventRegistrationState"]
    }
  }
  "/api/v1/events/{event_id}/cancel-registration": {
    post: {
      response: components["schemas"]["EventRegistrationState"]
    }
  }
  "/api/v1/events/{event_id}/save": {
    post: {
      response: components["schemas"]["SavedEventState"]
    }
    delete: {
      response: components["schemas"]["SavedEventState"]
    }
  }
  "/api/v1/payments/events/{event_id}/checkout": {
    post: {
      response: components["schemas"]["EventCheckoutSession"]
      body: components["schemas"]["EventCheckoutRequest"]
    }
  }
  "/api/v1/payments/admin/payments": {
    get: {
      response: Array<components["schemas"]["PaymentAdminRecord"]>
    }
  }
  "/api/v1/payments/admin/payments/{payment_id}/refund": {
    post: {
      response: components["schemas"]["PaymentAdminActionResult"]
      body: components["schemas"]["PaymentRefundRequest"]
    }
  }
  "/api/v1/payments/admin/payments/{payment_id}/disputes": {
    post: {
      response: components["schemas"]["PaymentAdminActionResult"]
      body: components["schemas"]["PaymentDisputeRequest"]
    }
  }
  "/api/v1/payments/moyasar/webhook": {
    post: {
      response: components["schemas"]["MoyasarWebhookResult"]
      body: components["schemas"]["MoyasarWebhookPayload"]
    }
  }
  "/api/v1/search": {
    get: {
      response: Array<components["schemas"]["SearchResult"]>
    }
  }
  "/api/v1/recommendations/events": {
    post: {
      response: components["schemas"]["RecommendationEventState"]
      body: components["schemas"]["RecommendationEventCreate"]
    }
  }
  "/health": {
    get: {
      response: Record<string, string>
    }
  }
}
