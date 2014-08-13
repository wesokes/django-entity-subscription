from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from django_dynamic_fixture import G, N
from entity.models import Entity, EntityRelationship
from mock import patch
from datetime import datetime

from entity_subscription.models import (
    Medium, Action, Subscription, Unsubscribe, Notification, NotificationMedium)


class SubscriptionManagerMediumsSubscribedTest(TestCase):
    # We just test that this dispatches correctly. We test the
    # dispatched functions more carefully.
    @patch('entity_subscription.models.SubscriptionManager._mediums_subscribed_individual')
    def test_individual(self, subscribed_mock):
        action = N(Action)
        entity = N(Entity)
        Subscription.objects.mediums_subscribed(action, entity)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)

    @patch('entity_subscription.models.SubscriptionManager._mediums_subscribed_group')
    def test_group(self, subscribed_mock):
        action = N(Action)
        entity = N(Entity)
        ct = N(ContentType)
        Subscription.objects.mediums_subscribed(action, entity, ct)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)


class SubscriptionManagerIsSubscribedTest(TestCase):
    # We just test that this dispatches correctly. We test the
    # dispatched functions more carefully.
    @patch('entity_subscription.models.SubscriptionManager._is_subscribed_individual')
    def test_individual(self, subscribed_mock):
        action = N(Action)
        medium = N(Medium)
        entity = N(Entity)
        Subscription.objects.is_subscribed(action, medium, entity)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)

    @patch('entity_subscription.models.SubscriptionManager._is_subscribed_group')
    def test_group(self, subscribed_mock):
        action = N(Action)
        medium = N(Medium)
        entity = N(Entity)
        ct = N(ContentType)
        Subscription.objects.is_subscribed(action, medium, entity, ct)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)


class SubscriptionManagerMediumsSubscribedIndividualTest(TestCase):
    def setUp(self):
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.action_1 = G(Action)
        self.action_2 = G(Action)

    def test_individual_subscription(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(action=self.action_1, entity=entity_1)
        expected_medium = self.medium_1
        self.assertEqual(mediums.first(), expected_medium)

    def test_group_subscription(self):
        ct = G(ContentType)
        super_e = G(Entity)
        sub_e = G(Entity, entity_type=ct)
        G(EntityRelationship, super_entity=super_e, sub_entity=sub_e)
        G(Subscription, entity=super_e, medium=self.medium_1, action=self.action_1, subentity_type=ct)
        mediums = Subscription.objects._mediums_subscribed_individual(action=self.action_1, entity=sub_e)
        expected_medium = self.medium_1
        self.assertEqual(mediums.first(), expected_medium)

    def test_multiple_mediums(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, action=self.action_1, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(action=self.action_1, entity=entity_1)
        self.assertEqual(mediums.count(), 2)

    def test_unsubscribed(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, action=self.action_1, subentity_type=None)
        G(Unsubscribe, entity=entity_1, medium=self.medium_1, action=self.action_1)
        mediums = Subscription.objects._mediums_subscribed_individual(action=self.action_1, entity=entity_1)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_2)

    def test_filters_by_action(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, action=self.action_2, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(action=self.action_1, entity=entity_1)
        self.assertEqual(mediums.count(), 1)


class SubscriptionManagerMediumsSubscribedGroup(TestCase):
    def setUp(self):
        self.ct = G(ContentType)
        self.action_1 = G(Action)
        self.action_2 = G(Action)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)

    def test_one_subscription_matches_across_supers(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.action_1, super_2, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)

    def test_multiple_subscriptions_match_across_supers(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        super_3 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(EntityRelationship, super_entity=super_3, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        G(Subscription, entity=super_2, medium=self.medium_2, action=self.action_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.action_1, super_3, self.ct)
        self.assertEqual(mediums.count(), 2)

    def test_filters_by_action(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        G(Subscription, entity=super_1, medium=self.medium_2, action=self.action_2, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.action_1, super_2, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)

    def test_filters_by_super_entity_intersections(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        super_3 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_3, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        G(Subscription, entity=super_2, medium=self.medium_2, action=self.action_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.action_1, super_3, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)


class SubscriptionManagerIsSubScribedIndividualTest(TestCase):
    def setUp(self):
        self.ct = G(ContentType)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.action_1 = G(Action)
        self.action_2 = G(Action)
        self.entity_1 = G(Entity, entity_type=self.ct)
        self.entity_2 = G(Entity)
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_2)

    def test_is_subscribed_direct_subscription(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertTrue(is_subscribed)

    def test_is_subscribed_group_subscription(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertTrue(is_subscribed)

    def test_filters_action(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, action=self.action_2, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_medium(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_2, action=self.action_1, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_super_entity_means_not_subscribed(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, action=self.action_1, subentity_type=self.ct)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_not_subscribed(self):
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_unsubscribed(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, action=self.action_1, subentity_type=None)
        G(Unsubscribe, entity=self.entity_1, medium=self.medium_1, action=self.action_1)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.action_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)


class SubscriptionManagerIsSubscribedGroupTest(TestCase):
    def setUp(self):
        self.ct_1 = G(ContentType)
        self.ct_2 = G(ContentType)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.action_1 = G(Action)
        self.action_2 = G(Action)
        self.entity_1 = G(Entity, entity_type=self.ct_1)    # sub
        self.entity_2 = G(Entity)                           # super
        self.entity_3 = G(Entity)                           # super
        self.entity_4 = G(Entity, entity_type=self.ct_2)    # sub
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_2)
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_3)
        G(EntityRelationship, sub_entity=self.entity_4, super_entity=self.entity_2)
        G(EntityRelationship, sub_entity=self.entity_4, super_entity=self.entity_3)

    def test_one_subscription_matches_across_supers(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, action=self.action_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            action=self.action_1, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertTrue(is_subscribed)

    def test_filters_action(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, action=self.action_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            action=self.action_2, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_medium(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, action=self.action_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            action=self.action_1, medium=self.medium_2, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_subentity_type(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, action=self.action_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            action=self.action_1, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_2
        )
        self.assertFalse(is_subscribed)


class SubscriptionFilterNotSubscribedTest(TestCase):
    def setUp(self):
        self.super_ct = G(ContentType)
        self.sub_ct = G(ContentType)
        self.super_e1 = G(Entity, entity_type=self.super_ct)
        self.super_e2 = G(Entity, entity_type=self.super_ct)
        self.sub_e1 = G(Entity, entity_type=self.sub_ct)
        self.sub_e2 = G(Entity, entity_type=self.sub_ct)
        self.sub_e3 = G(Entity, entity_type=self.sub_ct)
        self.sub_e4 = G(Entity, entity_type=self.sub_ct)
        self.ind_e1 = G(Entity, entity_type=self.sub_ct)
        self.ind_e2 = G(Entity, entity_type=self.sub_ct)
        self.medium = G(Medium)
        self.action = G(Action)
        G(EntityRelationship, sub_entity=self.sub_e1, super_entity=self.super_e1)
        G(EntityRelationship, sub_entity=self.sub_e2, super_entity=self.super_e1)
        G(EntityRelationship, sub_entity=self.sub_e3, super_entity=self.super_e2)
        G(EntityRelationship, sub_entity=self.sub_e4, super_entity=self.super_e2)

    def test_group_and_individual_subscription(self):
        G(Subscription, entity=self.ind_e1, action=self.action, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, action=self.action, medium=self.medium, subentity_type=self.sub_ct)
        entities = [self.sub_e1, self.sub_e3, self.ind_e1, self.ind_e2]
        filtered_entities = Subscription.objects.filter_not_subscribed(self.action, self.medium, entities)
        expected_entity_ids = [self.sub_e1.id, self.ind_e1.id]
        self.assertEqual(set(filtered_entities.values_list('id', flat=True)), set(expected_entity_ids))

    def test_unsubscribe_filtered_out(self):
        G(Subscription, entity=self.ind_e1, action=self.action, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, action=self.action, medium=self.medium, subentity_type=self.sub_ct)
        G(Unsubscribe, entity=self.sub_e1, action=self.action, medium=self.medium)
        entities = [self.sub_e1, self.sub_e2, self.sub_e3, self.ind_e1, self.ind_e2]
        filtered_entities = Subscription.objects.filter_not_subscribed(self.action, self.medium, entities)
        expected_entity_ids = [self.sub_e2.id, self.ind_e1.id]
        self.assertEqual(set(filtered_entities.values_list('id', flat=True)), set(expected_entity_ids))

    def test_entities_not_passed_in_filtered(self):
        G(Subscription, entity=self.ind_e1, action=self.action, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, action=self.action, medium=self.medium, subentity_type=self.sub_ct)
        entities = list(self.super_e1.get_sub_entities().is_any_type(self.sub_ct))
        filtered_entities = Subscription.objects.filter_not_subscribed(self.action, self.medium, entities)
        self.assertEqual(set(filtered_entities), set(entities))

    def test_different_entity_types_raises_error(self):
        entities = [self.sub_e1, self.super_e1]
        with self.assertRaises(ValueError):
            Subscription.objects.filter_not_subscribed(self.action, self.medium, entities)


class UnsubscribeManagerIsUnsubscribed(TestCase):
    def test_is_unsubscribed(self):
        entity, action, medium = G(Entity), G(Action), G(Medium)
        G(Unsubscribe, entity=entity, action=action, medium=medium)
        is_unsubscribed = Unsubscribe.objects.is_unsubscribed(action, medium, entity)
        self.assertTrue(is_unsubscribed)

    def test_is_not_unsubscribed(self):
        entity, action, medium = G(Entity), G(Action), G(Medium)
        is_unsubscribed = Unsubscribe.objects.is_unsubscribed(action, medium, entity)
        self.assertFalse(is_unsubscribed)


class NumberOfQueriesTests(TestCase):
    def test_query_count(self):
        ct = G(ContentType)
        e0 = G(Entity, entity_type=ct)   # sub
        e1 = G(Entity, entity_type=ct)   # sub
        e2 = G(Entity)                   # super
        e3 = G(Entity)                   # super
        e4 = G(Entity)                   # super
        e5 = G(Entity)                   # super
        e6 = G(Entity)                   # super
        m1, m2, m3, m4, m5 = G(Medium), G(Medium), G(Medium), G(Medium), G(Medium)
        s1, s2 = G(Action), G(Action)
        G(EntityRelationship, sub_entity=e1, super_entity=e2, subentity_type=ct)
        G(EntityRelationship, sub_entity=e1, super_entity=e3, subentity_type=ct)
        G(EntityRelationship, sub_entity=e1, super_entity=e4, subentity_type=ct)
        G(EntityRelationship, sub_entity=e1, super_entity=e5, subentity_type=ct)
        G(EntityRelationship, sub_entity=e1, super_entity=e6, subentity_type=ct)

        G(EntityRelationship, sub_entity=e0, super_entity=e2, subentity_type=ct)
        G(EntityRelationship, sub_entity=e0, super_entity=e3, subentity_type=ct)
        G(EntityRelationship, sub_entity=e0, super_entity=e4, subentity_type=ct)
        G(EntityRelationship, sub_entity=e0, super_entity=e5, subentity_type=ct)
        G(EntityRelationship, sub_entity=e0, super_entity=e6, subentity_type=ct)

        G(Subscription, entity=e2, subentity_type=ct, action=s1, medium=m1)
        G(Subscription, entity=e3, subentity_type=ct, action=s1, medium=m2)
        G(Subscription, entity=e4, subentity_type=ct, action=s1, medium=m3)
        G(Subscription, entity=e5, subentity_type=ct, action=s1, medium=m4)
        G(Subscription, entity=e6, subentity_type=ct, action=s1, medium=m5)

        G(Subscription, entity=e2, subentity_type=ct, action=s2, medium=m1)
        G(Subscription, entity=e3, subentity_type=ct, action=s2, medium=m2)
        G(Subscription, entity=e4, subentity_type=ct, action=s2, medium=m3)
        G(Subscription, entity=e5, subentity_type=ct, action=s2, medium=m4)
        G(Subscription, entity=e6, subentity_type=ct, action=s2, medium=m5)

        with self.assertNumQueries(1):
            mediums = Subscription.objects._mediums_subscribed_individual(action=s1, entity=e1)
            list(mediums)

        with self.assertNumQueries(1):
            mediums = Subscription.objects._mediums_subscribed_group(action=s1, entity=e6, subentity_type=ct)
            list(mediums)

        with self.assertNumQueries(2):
            Subscription.objects._is_subscribed_individual(action=s1, medium=m1, entity=e1)

        with self.assertNumQueries(1):
            Subscription.objects._is_subscribed_group(action=s1, medium=m1, entity=e6, subentity_type=ct)

        with self.assertNumQueries(1):
            entities = [e0, e1]
            list(Subscription.objects.filter_not_subscribed(action=s1, medium=m1, entities=entities))


class UnicodeMethodTests(TestCase):
    def setUp(self):
        self.entity = G(
            Entity, entity_meta={'name': 'Entity Test'}
        )
        self.medium = G(
            Medium, name='test', display_name='Test', description='A test medium.'
        )
        self.action = G(
            Action, name='test', display_name='Test', description='A test action.'
        )

    def test_subscription_unicode(self):
        sub = G(Subscription, entity=self.entity, medium=self.medium, action=self.action)
        expected_unicode = 'Entity Test to Test by Test'
        self.assertEqual(sub.__unicode__(), expected_unicode)

    def test_unsubscribe_unicode(self):
        unsub = G(Unsubscribe, entity=self.entity, medium=self.medium, action=self.action)
        expected_unicode = 'Entity Test from Test by Test'
        self.assertEqual(unsub.__unicode__(), expected_unicode)

    def test_medium_unicode(self):
        expected_unicode = 'Test'
        self.assertEqual(self.medium.__unicode__(), expected_unicode)

    def test_action_unicode(self):
        expected_unicode = 'Test'
        self.assertEqual(self.action.__unicode__(), expected_unicode)


class NotificationQuerySetMediumTest(TestCase):
    def setUp(self):
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.note_1 = G(Notification, context={})
        self.note_2 = G(Notification, context={})

    def test_basic_medium_filtering(self):
        G(NotificationMedium, notification=self.note_1, medium=self.medium_1)
        G(NotificationMedium, notification=self.note_2, medium=self.medium_2)
        medium_1_notifications = Notification.objects.all().medium(medium=self.medium_1)
        self.assertEqual(medium_1_notifications.count(), 1)
        self.assertEqual(medium_1_notifications.first(), self.note_1)

    def test_time_seen_filtering(self):
        G(NotificationMedium, notification=self.note_1, medium=self.medium_1)
        G(NotificationMedium, notification=self.note_2, medium=self.medium_1, time_seen=datetime(2013, 1, 1))
        medium_1_notifications = Notification.objects.all().medium(medium=self.medium_1, include_seen=False)
        self.assertEqual(medium_1_notifications.count(), 1)
        self.assertEqual(medium_1_notifications.first(), self.note_1)


class NotificationQuerySetMarkSeenTest(TestCase):
    def setUp(self):
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.note_1 = G(Notification, context={})
        self.note_2 = G(Notification, context={})

    def test_marks_seen(self):
        G(NotificationMedium, medium=self.medium_1, notification=self.note_1)
        Notification.objects.all().mark_seen(for_medium=self.medium_1)
        self.assertTrue(NotificationMedium.objects.first().time_seen is not None)

    def test_does_not_mark_previously_seen(self):
        seen_time = datetime(2013, 01, 01)
        G(
            NotificationMedium, medium=self.medium_1,
            notification=self.note_1, time_seen=seen_time
        )
        marked_count = Notification.objects.all().mark_seen(for_medium=self.medium_1)
        self.assertEqual(marked_count, 0)
        self.assertEqual(NotificationMedium.objects.first().time_seen, seen_time)

    def test_filters_by_medium(self):
        G(NotificationMedium, medium=self.medium_1, notification=self.note_1)
        G(NotificationMedium, medium=self.medium_2, notification=self.note_1)
        marked_count = Notification.objects.all().mark_seen(for_medium=self.medium_1)
        self.assertEqual(marked_count, 1)

    def test_marks_for_multiple_notifications(self):
        G(NotificationMedium, medium=self.medium_1, notification=self.note_1)
        G(NotificationMedium, medium=self.medium_1, notification=self.note_2)
        marked_count = Notification.objects.all().mark_seen(for_medium=self.medium_1)
        self.assertEqual(marked_count, 2)


class NotificationManagerMediumTest(TestCase):
    @patch('entity_subscription.models.NotificationQuerySet.medium')
    def test_calls_queryset_method(self, medium_mock):
        Notification.objects.medium(medium=N(Medium))
        self.assertTrue(len(medium_mock.mock_calls), 1)


class NotificationManagerMarkSeen(TestCase):
    @patch('entity_subscription.models.NotificationQuerySet.mark_seen')
    def test_calls_queryset_method(self, mark_seen_mock):
        Notification.objects.mark_seen(for_medium=N(Medium))
        self.assertTrue(len(mark_seen_mock.mock_calls), 1)


class NotificationManagerCreateNotificationTest(TestCase):
    def setUp(self):
        self.actor = G(Entity)
        self.action = G(Action, name='test_action')
        self.action_object = G(Entity)
        self.target = G(Entity)

    def test_creates_notification(self):
        Notification.objects.create_notification(
            action=self.action,
            actor=self.actor,
            context={},
        )
        self.assertEqual(Notification.objects.count(), 1)

    def test_creates_unique_event_ids(self):
        notification_1 = Notification.objects.create_notification(
            action=self.action,
            actor=self.actor,
            context={},
        )
        notification_2 = Notification.objects.create_notification(
            action=self.action,
            actor=self.actor,
            context={},
        )
        self.assertNotEqual(notification_1.event_id, notification_2.event_id)

    def test_raises_bad_data_error(self):
        Notification.objects.create_notification(
            action=self.action,
            actor=self.actor,
            context={},
            event_id='Not Going To Be Unique',
        )
        with self.assertRaises(IntegrityError):
            Notification.objects.create_notification(
                action=self.action,
                actor=self.actor,
                context={},
                event_id='Not Going To Be Unique',
            )


class NotificationQueryBaseTest(TestCase):
    def setUp(self):
        super(NotificationQueryBaseTest, self).setUp()
        self.team_content_type = G(ContentType)
        self.user_content_type = G(ContentType)

        self.news_feed_medium = G(Medium, name='news_feed', display_name='News Feed')
        self.email_medium = G(Medium, name='email', display_name='Email')

        self.woke_up_action = G(Action, name='action1', display_name='woke up')
        self.punched_action = G(Action, name='action2', display_name='punched')
        self.high_fived_action = G(Action, name='action3', display_name='high fived')

        self.team_red = G(Entity, entity_type=self.team_content_type)
        self.team_blue = G(Entity, entity_type=self.team_content_type)

        self.user_wes = G(Entity, entity_type=self.user_content_type)
        self.user_jared = G(Entity, entity_type=self.user_content_type)
        self.user_josh = G(Entity, entity_type=self.user_content_type)
        self.user_jeff = G(Entity, entity_type=self.user_content_type)

        G(EntityRelationship, sub_entity=self.user_wes, super_entity=self.team_red)
        G(EntityRelationship, sub_entity=self.user_jared, super_entity=self.team_red)
        G(EntityRelationship, sub_entity=self.user_josh, super_entity=self.team_blue)
        G(EntityRelationship, sub_entity=self.user_jeff, super_entity=self.team_blue)

        self.jared_woke_up = Notification.objects.create_notification(self.woke_up_action, self.user_jared)
        self.jared_punched_josh = Notification.objects.create_notification(
            self.punched_action, self.user_jared, action_object=self.user_josh)
        self.jared_punched_jared = Notification.objects.create_notification(
            self.punched_action, self.user_jared, action_object=self.user_jared)
        self.jared_high_fived_jeff = Notification.objects.create_notification(
            self.high_fived_action, self.user_jared, action_object=self.user_jeff)
        self.josh_high_fived_wes = Notification.objects.create_notification(
            self.high_fived_action, self.user_josh, action_object=self.user_wes)
        self.wes_high_fived_jared = Notification.objects.create_notification(
            self.high_fived_action, self.user_wes, action_object=self.user_jared)
        self.jeff_woke_up = Notification.objects.create_notification(self.woke_up_action, self.user_jeff)


class NotificationIndividualQueryTest(NotificationQueryBaseTest):

    def test_individual_subscribe_entity_all_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])

    def test_individual_subscribe_entity_specific_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.punched_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_punched_josh, items[0])
        self.assertEqual(self.jared_punched_jared, items[1])

    def test_individual_subscribe_only_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.josh_high_fived_wes, items[1])
        self.assertEqual(self.wes_high_fived_jared, items[2])

    def test_individual_subscribe_subentity_all_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.wes_high_fived_jared, items[4])

    def test_individual_subscribe_subentity_specific_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])

    def test_individual_subscribe_different_medium(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.email_medium)
        self.assertEqual(0, queryset.count())


class NotificationIndividualQueryMultipleSubTest(NotificationQueryBaseTest):

    def test_individual_subscribe_entity_all_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.josh_high_fived_wes, items[4])

    def test_individual_subscribe_entity_specific_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.punched_action,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_punched_josh, items[0])
        self.assertEqual(self.jared_punched_jared, items[1])
        self.assertEqual(self.jared_high_fived_jeff, items[2])

    def test_individual_subscribe_only_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.woke_up_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_high_fived_jeff, items[1])
        self.assertEqual(self.josh_high_fived_wes, items[2])
        self.assertEqual(self.wes_high_fived_jared, items[3])
        self.assertEqual(self.jeff_woke_up, items[4])

    def test_individual_subscribe_subentity_all_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_blue, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(7, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.josh_high_fived_wes, items[4])
        self.assertEqual(self.wes_high_fived_jared, items[5])
        self.assertEqual(self.jeff_woke_up, items[6])

    def test_individual_subscribe_subentity_specific_actions(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None,
            followed_entity=self.team_blue, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.woke_up_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])
        self.assertEqual(self.jeff_woke_up, items[2])


class NotificationGroupQueryTest(NotificationQueryBaseTest):

    def test_group_subscribe_entity_all_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])

    def test_group_subscribe_entity_specific_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.punched_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_punched_josh, items[0])
        self.assertEqual(self.jared_punched_jared, items[1])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_punched_josh, items[0])
        self.assertEqual(self.jared_punched_jared, items[1])

    def test_group_subscribe_only_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.josh_high_fived_wes, items[1])
        self.assertEqual(self.wes_high_fived_jared, items[2])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.josh_high_fived_wes, items[1])
        self.assertEqual(self.wes_high_fived_jared, items[2])

    def test_group_subscribe_subentity_all_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.wes_high_fived_jared, items[4])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.wes_high_fived_jared, items[4])

    def test_group_subscribe_subentity_specific_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(2, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])

    def test_group_subscribe_different_medium(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_jared, self.email_medium)
        self.assertEqual(0, queryset.count())

        queryset = Notification.objects.get_for_entity(self.user_wes, self.email_medium)
        self.assertEqual(0, queryset.count())


class NotificationGroupQueryMultipleSubTest(NotificationQueryBaseTest):

    def test_group_subscribe_entity_all_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_wes, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.wes_high_fived_jared, items[4])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.wes_high_fived_jared, items[4])

    def test_group_subscribe_entity_specific_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.punched_action,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.woke_up_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])

    def test_group_subscribe_only_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=None, followed_subentity_type=None,
            medium=self.news_feed_medium, action=self.woke_up_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_high_fived_jeff, items[1])
        self.assertEqual(self.josh_high_fived_wes, items[2])
        self.assertEqual(self.wes_high_fived_jared, items[3])
        self.assertEqual(self.jeff_woke_up, items[4])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(5, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_high_fived_jeff, items[1])
        self.assertEqual(self.josh_high_fived_wes, items[2])
        self.assertEqual(self.wes_high_fived_jared, items[3])
        self.assertEqual(self.jeff_woke_up, items[4])

    def test_group_subscribe_subentity_all_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_blue, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=None,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(7, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.josh_high_fived_wes, items[4])
        self.assertEqual(self.wes_high_fived_jared, items[5])
        self.assertEqual(self.jeff_woke_up, items[6])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(7, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])
        self.assertEqual(self.josh_high_fived_wes, items[4])
        self.assertEqual(self.wes_high_fived_jared, items[5])
        self.assertEqual(self.jeff_woke_up, items[6])

    def test_group_subscribe_subentity_specific_actions(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_red, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.high_fived_action,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.team_blue, followed_subentity_type=self.user_content_type,
            medium=self.news_feed_medium, action=self.woke_up_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])
        self.assertEqual(self.jeff_woke_up, items[2])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_high_fived_jeff, items[0])
        self.assertEqual(self.wes_high_fived_jared, items[1])
        self.assertEqual(self.jeff_woke_up, items[2])


class NotificationUnsubscribeTest(NotificationQueryBaseTest):

    def test_individual_unsubscribe_entity(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=self.user_jared, medium=self.news_feed_medium, action=None,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(1, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.josh_high_fived_wes, items[0])

    def test_individual_unsubscribe_action(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=None, medium=self.news_feed_medium, action=self.punched_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_high_fived_jeff, items[1])
        self.assertEqual(self.josh_high_fived_wes, items[2])

    def test_individual_unsubscribe_entity_action(self):
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.user_wes, subentity_type=None, followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=self.user_jared, medium=self.news_feed_medium,
            action=self.high_fived_action,
        )

        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.josh_high_fived_wes, items[3])

    def test_group_unsubscribe_entity(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=self.user_jared, medium=self.news_feed_medium,
            action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_jared, followed_entity=self.user_josh, medium=self.news_feed_medium,
            action=None,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(1, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.josh_high_fived_wes, items[0])

    def test_group_unsubscribe_action(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=None, medium=self.news_feed_medium,
            action=self.punched_action,
        )
        G(
            Unsubscribe,
            entity=self.user_jared, followed_entity=None, medium=self.news_feed_medium,
            action=self.high_fived_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(3, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_high_fived_jeff, items[1])
        self.assertEqual(self.josh_high_fived_wes, items[2])

    def test_group_unsubscribe_entity_action(self):
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_jared, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Subscription,
            entity=self.team_red, subentity_type=self.user_content_type,
            followed_entity=self.user_josh, followed_subentity_type=None,
            medium=self.news_feed_medium, action=None,
        )
        G(
            Unsubscribe,
            entity=self.user_wes, followed_entity=self.user_jared, medium=self.news_feed_medium,
            action=self.high_fived_action,
        )
        G(
            Unsubscribe,
            entity=self.user_jared, followed_entity=self.user_josh, medium=self.news_feed_medium,
            action=self.high_fived_action,
        )

        # check for jared
        queryset = Notification.objects.get_for_entity(self.user_jared, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.jared_high_fived_jeff, items[3])

        # check for wes
        queryset = Notification.objects.get_for_entity(self.user_wes, self.news_feed_medium)
        self.assertEqual(4, queryset.count())

        # check notification objects
        items = list(queryset.order_by('time_created'))
        self.assertEqual(self.jared_woke_up, items[0])
        self.assertEqual(self.jared_punched_josh, items[1])
        self.assertEqual(self.jared_punched_jared, items[2])
        self.assertEqual(self.josh_high_fived_wes, items[3])
