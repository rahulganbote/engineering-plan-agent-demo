# BRD: Real-Time Notification System

**Document Version:** 1.2  
**Author:** Product Team  
**Date:** 2024-11-15  
**Status:** Ready for Engineering Review  

---

## Executive Summary

The platform currently has no real-time notification capability. Users miss important updates because they must manually refresh to see changes. This BRD defines the requirements for a real-time notification system to improve user engagement and reduce churn driven by missed updates.

---

## Background and Problem Statement

User research conducted in Q3 showed that 38% of users who churned in the prior 6 months cited "missing important updates" as a contributing factor. Support ticket volume related to "I didn't know X happened" averages 200/week. 

Competitor platforms (including three direct competitors) offer real-time or near-real-time notification delivery. Our current polling-based approach (30-second refresh) creates a perceived lag that users describe as "the app feeling slow."

---

## Goals

- Deliver in-app notifications within 2 seconds of a triggering event
- Allow users to configure which notifications they receive, per notification type
- Support push notifications for users who are not actively using the app
- Reduce notification-related support tickets by 60% within 3 months of launch
- Not degrade existing page performance metrics (LCP, TTI) by more than 5%

---

## Non-Goals

- This is not a re-architecture of the existing activity feed
- This is not a marketing push notification system (separate project, Q2 next year)
- This does not include SMS or email notification channels in v1

---

## Functional Requirements

### FR-001: Real-Time In-App Notifications
Users must receive in-app notifications within 2 seconds of the triggering event occurring on the server. This applies while the user has the application open in any tab.

### FR-002: Notification Preference Management
Users must be able to configure notification preferences at the notification-type level. Configuration options are: enabled, disabled, or "batched" (delivered as a digest at a user-specified frequency). Preferences must persist across sessions.

### FR-003: Push Notifications (Background)
Users who are not actively in the app must receive push notifications for P0-tier events (as defined by the product team). Push delivery must occur within 30 seconds of the triggering event. This requires mobile support (iOS and Android) and web push.

### FR-004: Notification Inbox
Users must be able to access a notification inbox showing the last 90 days of notifications. Inbox items must be marked read/unread and support bulk actions (mark all read, delete).

### FR-005: Notification Badges
Unread notification counts must be reflected in the application navigation in real time.

---

## Non-Functional Requirements

### NFR-001: Scale
The system must support 50,000 concurrent connected users at launch, scaling to 200,000 within 12 months without architectural changes.

### NFR-002: Reliability
Notification delivery must have a p99 latency under 5 seconds for in-app delivery. The system must have 99.9% uptime.

### NFR-003: Performance
The notification system must not increase page LCP or TTI by more than 5% on any existing page.

### NFR-004: Security
Notifications must only be delivered to the correct user. The system must enforce authentication at the connection layer. No cross-user notification delivery is permissible under any failure mode.

---

## Open Questions

1. **Push notification provider:** Firebase Cloud Messaging vs. Apple Push Notification Service vs. a unified provider (e.g., Expo, OneSignal)? This decision affects both the implementation approach and vendor costs.
2. **Notification retention:** Should notifications older than 90 days be hard-deleted or soft-deleted/archived?
3. **Rate limiting:** Is there a maximum number of notifications a user can receive per hour before we throttle or batch?
4. **Digest frequency options:** For "batched" notification preference, what are the allowed digest frequencies? (Hourly, daily, weekly?)
5. **WebSocket vs. SSE:** Engineering to recommend; product has no preference.

---

## Success Metrics

| Metric | Baseline | Target (90 days post-launch) |
|---|---|---|
| In-app delivery latency (p50) | N/A (polling) | < 1 second |
| In-app delivery latency (p99) | N/A | < 5 seconds |
| Notification-related support tickets | 200/week | < 80/week |
| User notification preference adoption | N/A | > 40% of users configure at least one preference |
| Push notification opt-in rate | N/A | > 30% of mobile users |

---

## Dependencies

- **Auth service:** Connection-layer authentication relies on the existing JWT-based auth service
- **Event bus:** Triggering events will be sourced from the internal event bus (Kafka); event schema definitions needed from data platform team
- **Mobile apps:** iOS and Android apps require updates to support push registration; mobile team capacity needed in Q1
- **Infrastructure:** WebSocket connection management at scale may require infrastructure changes; infra team review requested

---

## Timeline

Product is targeting a **Q1 launch** for FR-001, FR-002, and FR-005 (in-app + preferences + badges). FR-003 (push) and FR-004 (inbox) are targeted for **Q2**.

Engineering is asked to assess feasibility and surface any timeline risks in the planning document.

---

## Stakeholders

| Role | Name | Involvement |
|---|---|---|
| Product Lead | [Name] | Requirements owner |
| Engineering Lead | [Name] | Plan owner |
| Mobile Lead | [Name] | Push notification integration |
| Infra Lead | [Name] | Scale and reliability review |
| Design Lead | [Name] | Notification UI components |
