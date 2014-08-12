from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.test import TestCase
from django_dynamic_fixture import G, N
from entity.models import Entity, EntityRelationship
from mock import patch
from datetime import datetime, timedelta
from freezegun import freeze_time

from entity_subscription.models import Medium, Source, Subscription, Unsubscribe, Notification, NotificationMedium


class SubscriptionManagerMediumsSubscribedTest(TestCase):
    # We just test that this dispatches correctly. We test the
    # dispatched functions more carefully.
    @patch('entity_subscription.models.SubscriptionManager._mediums_subscribed_individual')
    def test_individual(self, subscribed_mock):
        source = N(Source)
        entity = N(Entity)
        Subscription.objects.mediums_subscribed(source, entity)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)

    @patch('entity_subscription.models.SubscriptionManager._mediums_subscribed_group')
    def test_group(self, subscribed_mock):
        source = N(Source)
        entity = N(Entity)
        ct = N(ContentType)
        Subscription.objects.mediums_subscribed(source, entity, ct)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)


class SubscriptionManagerIsSubscribedTest(TestCase):
    # We just test that this dispatches correctly. We test the
    # dispatched functions more carefully.
    @patch('entity_subscription.models.SubscriptionManager._is_subscribed_individual')
    def test_individual(self, subscribed_mock):
        source = N(Source)
        medium = N(Medium)
        entity = N(Entity)
        Subscription.objects.is_subscribed(source, medium, entity)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)

    @patch('entity_subscription.models.SubscriptionManager._is_subscribed_group')
    def test_group(self, subscribed_mock):
        source = N(Source)
        medium = N(Medium)
        entity = N(Entity)
        ct = N(ContentType)
        Subscription.objects.is_subscribed(source, medium, entity, ct)
        self.assertEqual(len(subscribed_mock.mock_calls), 1)


class SubscriptionManagerMediumsSubscribedIndividualTest(TestCase):
    def setUp(self):
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.source_1 = G(Source)
        self.source_2 = G(Source)

    def test_individual_subscription(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(source=self.source_1, entity=entity_1)
        expected_medium = self.medium_1
        self.assertEqual(mediums.first(), expected_medium)

    def test_group_subscription(self):
        ct = G(ContentType)
        super_e = G(Entity)
        sub_e = G(Entity, entity_type=ct)
        G(EntityRelationship, super_entity=super_e, sub_entity=sub_e)
        G(Subscription, entity=super_e, medium=self.medium_1, source=self.source_1, subentity_type=ct)
        mediums = Subscription.objects._mediums_subscribed_individual(source=self.source_1, entity=sub_e)
        expected_medium = self.medium_1
        self.assertEqual(mediums.first(), expected_medium)

    def test_multiple_mediums(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, source=self.source_1, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(source=self.source_1, entity=entity_1)
        self.assertEqual(mediums.count(), 2)

    def test_unsubscribed(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, source=self.source_1, subentity_type=None)
        G(Unsubscribe, entity=entity_1, medium=self.medium_1, source=self.source_1)
        mediums = Subscription.objects._mediums_subscribed_individual(source=self.source_1, entity=entity_1)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_2)

    def test_filters_by_source(self):
        entity_1 = G(Entity)
        G(Subscription, entity=entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        G(Subscription, entity=entity_1, medium=self.medium_2, source=self.source_2, subentity_type=None)
        mediums = Subscription.objects._mediums_subscribed_individual(source=self.source_1, entity=entity_1)
        self.assertEqual(mediums.count(), 1)


class SubscriptionManagerMediumsSubscribedGroup(TestCase):
    def setUp(self):
        self.ct = G(ContentType)
        self.source_1 = G(Source)
        self.source_2 = G(Source)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)

    def test_one_subscription_matches_across_supers(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.source_1, super_2, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)

    def test_multiple_subscriptions_match_acorss_supers(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        super_3 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(EntityRelationship, super_entity=super_3, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        G(Subscription, entity=super_2, medium=self.medium_2, source=self.source_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.source_1, super_3, self.ct)
        self.assertEqual(mediums.count(), 2)

    def test_filters_by_source(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_2, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        G(Subscription, entity=super_1, medium=self.medium_2, source=self.source_2, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.source_1, super_2, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)

    def test_filters_by_super_entity_intersections(self):
        super_1 = G(Entity)
        super_2 = G(Entity)
        super_3 = G(Entity)
        sub = G(Entity, entity_type=self.ct)
        G(EntityRelationship, super_entity=super_1, sub_entity=sub)
        G(EntityRelationship, super_entity=super_3, sub_entity=sub)
        G(Subscription, entity=super_1, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        G(Subscription, entity=super_2, medium=self.medium_2, source=self.source_1, subentity_type=self.ct)
        mediums = Subscription.objects._mediums_subscribed_group(self.source_1, super_3, self.ct)
        self.assertEqual(mediums.count(), 1)
        self.assertEqual(mediums.first(), self.medium_1)


class SubscriptionManagerIsSubScribedIndividualTest(TestCase):
    def setUp(self):
        self.ct = G(ContentType)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.source_1 = G(Source)
        self.source_2 = G(Source)
        self.entity_1 = G(Entity, entity_type=self.ct)
        self.entity_2 = G(Entity)
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_2)

    def test_is_subscribed_direct_subscription(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertTrue(is_subscribed)

    def test_is_subscribed_group_subscription(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertTrue(is_subscribed)

    def test_filters_source(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, source=self.source_2, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_medium(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_2, source=self.source_1, subentity_type=None)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_super_entity_means_not_subscribed(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, source=self.source_1, subentity_type=self.ct)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_not_subscribed(self):
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)

    def test_unsubscribed(self):
        G(Subscription, entity=self.entity_1, medium=self.medium_1, source=self.source_1, subentity_type=None)
        G(Unsubscribe, entity=self.entity_1, medium=self.medium_1, source=self.source_1)
        is_subscribed = Subscription.objects._is_subscribed_individual(
            self.source_1, self.medium_1, self.entity_1
        )
        self.assertFalse(is_subscribed)


class SubscriptionManagerIsSubscribedGroupTest(TestCase):
    def setUp(self):
        self.ct_1 = G(ContentType)
        self.ct_2 = G(ContentType)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)
        self.source_1 = G(Source)
        self.source_2 = G(Source)
        self.entity_1 = G(Entity, entity_type=self.ct_1)    # sub
        self.entity_2 = G(Entity)                           # super
        self.entity_3 = G(Entity)                           # super
        self.entity_4 = G(Entity, entity_type=self.ct_2)    # sub
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_2)
        G(EntityRelationship, sub_entity=self.entity_1, super_entity=self.entity_3)
        G(EntityRelationship, sub_entity=self.entity_4, super_entity=self.entity_2)
        G(EntityRelationship, sub_entity=self.entity_4, super_entity=self.entity_3)

    def test_one_subscription_matches_across_supers(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, source=self.source_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            source=self.source_1, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertTrue(is_subscribed)

    def test_filters_source(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, source=self.source_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            source=self.source_2, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_medium(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, source=self.source_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            source=self.source_1, medium=self.medium_2, entity=self.entity_3, subentity_type=self.ct_1
        )
        self.assertFalse(is_subscribed)

    def test_filters_subentity_type(self):
        G(Subscription, entity=self.entity_2, medium=self.medium_1, source=self.source_1, subentity_type=self.ct_1)
        is_subscribed = Subscription.objects._is_subscribed_group(
            source=self.source_1, medium=self.medium_1, entity=self.entity_3, subentity_type=self.ct_2
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
        self.source = G(Source)
        G(EntityRelationship, sub_entity=self.sub_e1, super_entity=self.super_e1)
        G(EntityRelationship, sub_entity=self.sub_e2, super_entity=self.super_e1)
        G(EntityRelationship, sub_entity=self.sub_e3, super_entity=self.super_e2)
        G(EntityRelationship, sub_entity=self.sub_e4, super_entity=self.super_e2)

    def test_group_and_individual_subscription(self):
        G(Subscription, entity=self.ind_e1, source=self.source, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, source=self.source, medium=self.medium, subentity_type=self.sub_ct)
        entities = [self.sub_e1, self.sub_e3, self.ind_e1, self.ind_e2]
        filtered_entities = Subscription.objects.filter_not_subscribed(self.source, self.medium, entities)
        expected_entity_ids = [self.sub_e1.id, self.ind_e1.id]
        self.assertEqual(set(filtered_entities.values_list('id', flat=True)), set(expected_entity_ids))

    def test_unsubscribe_filtered_out(self):
        G(Subscription, entity=self.ind_e1, source=self.source, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, source=self.source, medium=self.medium, subentity_type=self.sub_ct)
        G(Unsubscribe, entity=self.sub_e1, source=self.source, medium=self.medium)
        entities = [self.sub_e1, self.sub_e2, self.sub_e3, self.ind_e1, self.ind_e2]
        filtered_entities = Subscription.objects.filter_not_subscribed(self.source, self.medium, entities)
        expected_entity_ids = [self.sub_e2.id, self.ind_e1.id]
        self.assertEqual(set(filtered_entities.values_list('id', flat=True)), set(expected_entity_ids))

    def test_entities_not_passed_in_filtered(self):
        G(Subscription, entity=self.ind_e1, source=self.source, medium=self.medium, subentity_type=None)
        G(Subscription, entity=self.super_e1, source=self.source, medium=self.medium, subentity_type=self.sub_ct)
        entities = list(self.super_e1.get_sub_entities().is_any_type(self.sub_ct))
        filtered_entities = Subscription.objects.filter_not_subscribed(self.source, self.medium, entities)
        self.assertEqual(set(filtered_entities), set(entities))

    def test_different_entity_types_raises_error(self):
        entities = [self.sub_e1, self.super_e1]
        with self.assertRaises(ValueError):
            Subscription.objects.filter_not_subscribed(self.source, self.medium, entities)


class UnsubscribeManagerIsUnsubscribed(TestCase):
    def test_is_unsubscribed(self):
        entity, source, medium = G(Entity), G(Source), G(Medium)
        G(Unsubscribe, entity=entity, source=source, medium=medium)
        is_unsubscribed = Unsubscribe.objects.is_unsubscribed(source, medium, entity)
        self.assertTrue(is_unsubscribed)

    def test_is_not_unsubscribed(self):
        entity, source, medium = G(Entity), G(Source), G(Medium)
        is_unsubscribed = Unsubscribe.objects.is_unsubscribed(source, medium, entity)
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
        s1, s2 = G(Source), G(Source)
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

        G(Subscription, entity=e2, subentity_type=ct, source=s1, medium=m1)
        G(Subscription, entity=e3, subentity_type=ct, source=s1, medium=m2)
        G(Subscription, entity=e4, subentity_type=ct, source=s1, medium=m3)
        G(Subscription, entity=e5, subentity_type=ct, source=s1, medium=m4)
        G(Subscription, entity=e6, subentity_type=ct, source=s1, medium=m5)

        G(Subscription, entity=e2, subentity_type=ct, source=s2, medium=m1)
        G(Subscription, entity=e3, subentity_type=ct, source=s2, medium=m2)
        G(Subscription, entity=e4, subentity_type=ct, source=s2, medium=m3)
        G(Subscription, entity=e5, subentity_type=ct, source=s2, medium=m4)
        G(Subscription, entity=e6, subentity_type=ct, source=s2, medium=m5)

        with self.assertNumQueries(1):
            mediums = Subscription.objects._mediums_subscribed_individual(source=s1, entity=e1)
            list(mediums)

        with self.assertNumQueries(1):
            mediums = Subscription.objects._mediums_subscribed_group(source=s1, entity=e6, subentity_type=ct)
            list(mediums)

        with self.assertNumQueries(2):
            Subscription.objects._is_subscribed_individual(source=s1, medium=m1, entity=e1)

        with self.assertNumQueries(1):
            Subscription.objects._is_subscribed_group(source=s1, medium=m1, entity=e6, subentity_type=ct)

        with self.assertNumQueries(1):
            entities = [e0, e1]
            list(Subscription.objects.filter_not_subscribed(source=s1, medium=m1, entities=entities))


class UnicodeMethodTests(TestCase):
    def setUp(self):
        self.entity = G(
            Entity, entity_meta={'name': 'Entity Test'}
        )
        self.medium = G(
            Medium, name='test', display_name='Test', description='A test medium.'
        )
        self.source = G(
            Source, name='test', display_name='Test', description='A test source.'
        )

    def test_subscription_unicode(self):
        sub = G(Subscription, entity=self.entity, medium=self.medium, source=self.source)
        expected_unicode = 'Entity Test to Test by Test'
        self.assertEqual(sub.__unicode__(), expected_unicode)

    def test_unsubscribe_unicode(self):
        unsub = G(Unsubscribe, entity=self.entity, medium=self.medium, source=self.source)
        expected_unicode = 'Entity Test from Test by Test'
        self.assertEqual(unsub.__unicode__(), expected_unicode)

    def test_medium_unicode(self):
        expected_unicode = 'Test'
        self.assertEqual(self.medium.__unicode__(), expected_unicode)

    def test_source_unicode(self):
        expected_unicode = 'Test'
        self.assertEqual(self.source.__unicode__(), expected_unicode)


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
        self.ct = G(ContentType)
        self.entity = G(Entity)
        self.sub_e = G(Entity, entity_type=self.ct)
        self.source = G(Source)
        self.medium_1 = G(Medium)
        self.medium_2 = G(Medium)

    def test_creates_notification(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
        )
        self.assertEqual(Notification.objects.count(), 1)

    @freeze_time("2013-01-22 00:00:00")
    def test_expiration_datetime(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        note = Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
            expires=timedelta(hours=1)
        )
        self.assertEqual(note.time_expires, datetime(2013, 1, 22, 1))

    @freeze_time("2013-01-22 00:00:00")
    def test_expiration_timedelta(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        note = Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
            expires=datetime(2013, 1, 22, 12)
        )
        self.assertEqual(note.time_expires, datetime(2013, 1, 22, 12))

    def test_not_subscribed(self):
        Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
        )
        self.assertFalse(Notification.objects.exists())

    def test_mediums_created(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_2, subentity_type=None)
        Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
        )
        self.assertEqual(NotificationMedium.objects.count(), 2)

    def test_mediums_list_restricts_mediums_created(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_2, subentity_type=None)
        Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
            mediums=[self.medium_1],
        )
        self.assertEqual(NotificationMedium.objects.count(), 1)
        self.assertEqual(NotificationMedium.objects.first().medium, self.medium_1)

    def test_subentity_type_group_notification(self):
        G(EntityRelationship, super_entity=self.entity, sub_entity=self.sub_e)
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=self.ct)
        note = Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
            subentity_type=self.ct,
        )
        self.assertEqual(note.subentity_type, self.ct)
        self.assertTrue(NotificationMedium.objects.exists())

    def test_creates_unique_uuids(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        notification_1 = Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
        )
        notification_2 = Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
        )
        self.assertNotEqual(notification_1.uuid, notification_2.uuid)

    def test_raises_bad_data_error(self):
        G(Subscription, entity=self.entity, source=self.source, medium=self.medium_1, subentity_type=None)
        Notification.objects.create_notification(
            entity=self.entity,
            notification_source=self.source,
            context={},
            uuid='Not Going To Be Unique',
        )
        with self.assertRaises(IntegrityError):
            Notification.objects.create_notification(
                entity=self.entity,
                notification_source=self.source,
                context={},
                uuid='Not Going To Be Unique',
            )
