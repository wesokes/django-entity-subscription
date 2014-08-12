from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from entity import Entity, EntityRelationship
import jsonfield
from datetime import timedelta
import datetime


class Medium(models.Model):
    """A method of actually delivering the notification to users.

    Mediums describe a particular method the application has of
    sending notifications. The code that handles actually sending the
    message should own a medium object that represents itself, or at
    least, know the name of one.
    """
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __unicode__(self):
        return self.display_name


class Source(models.Model):
    """A category of where notifications originate from.

    Sources should make sense as a category of notifications to users,
    and pieces of the application which create that type of
    notification should own a `source` object which they can pass
    along to the business logic for distributing the notificaiton.
    """
    name = models.CharField(max_length=64, unique=True)
    display_name = models.CharField(max_length=64)
    description = models.TextField()

    def __unicode__(self):
        return self.display_name


class SubscriptionManager(models.Manager):
    def mediums_subscribed(self, source, entity, subentity_type=None):
        """Return all mediums subscribed to for a source.

        Args:

          source - A `Source` object. Check the mediums subscribed to,
          for this source of notifications.

          entity - An `Entity` object. The entity to check
          subscriptions for.

          subentity_type - (Optional) A content_type indicating we're
          interested in the mediums subscribed to by all sub-entities
          of the `entity` argument matching this subentity_type.

        Returns:

           A queryset of mediums the entity is subscribed to.

           If the subentity_type is None, this queryset has all
           unsubscribed mediums filtered out.

           If the subentity_type is not None, this queryset contains
           all mediums that any of the subenties might be subscribed
           to, *without* any unsubscribed mediums filtered out.

        """
        if subentity_type is None:
            return self._mediums_subscribed_individual(source, entity)
        else:
            return self._mediums_subscribed_group(source, entity, subentity_type)

    def is_subscribed(self, source, medium, entity, subentity_type=None):
        """Return True if subscribed to this medium/source combination.

        Args:

          source - A `Source` object. Check that there is a
          subscription for this source and the given medium.

          medium - A `Medium` object. Check that there is a
          subscription for this medium and the given source

          entity - An `Entity` object. The entity to check
          subscriptions for.

          subentity_type - (Optional) A content_type indicating we're
          interested in the subscriptions by all sub-entities of the
          `entity` argument matching this subentity_type.

        Returns:

           A boolean indicating if the entity is subscribed to this
           source/medium combination.

           If the subentity_type is None, this boolean takes into
           account whether the entity is unsubscribed.

           If the subentity_type is not None, this boolean indicates
           that any of the subenties might be subscribed to this
           combination of source/medium, *without* any unsubscriptions
           filtered out.

        """
        if subentity_type is None:
            return self._is_subscribed_individual(source, medium, entity)
        else:
            return self._is_subscribed_group(source, medium, entity, subentity_type)

    def filter_not_subscribed(self, source, medium, entities):
        """Return only the entities subscribed to the source and medium.

        Args:

          source - A `Source` object. Check that there is a
          subscription for this source and the given medium.

          medium - A `Medium` object. Check that there is a
          subscription for this medium and the given source

          entities - An iterable of `Entity` objects. The iterable
          will be filtered down to only those with a subscription to
          the source and medium. All entities in this iterable must be
          of the same type.

        Raises:

          ValueError - if not all entities provided are of the same
          type.

        Returns:

          A queryset of entities which are in the initially provided
          list and are subscribed to the source and medium.

        """
        entity_type_id = entities[0].entity_type_id
        if not all(e.entity_type_id == entity_type_id for e in entities):
            msg = 'All entities provided must be of the same type.'
            raise ValueError(msg)

        group_subs = self.filter(source=source, medium=medium, subentity_type_id=entity_type_id)
        group_subscribed_entities = EntityRelationship.objects.filter(
            sub_entity__in=entities, super_entity__in=group_subs.values('entity')
        ).values_list('sub_entity', flat=True)

        individual_subs = self.filter(
            source=source, medium=medium, subentity_type=None
        ).values_list('entity', flat=True)

        relevant_unsubscribes = Unsubscribe.objects.filter(
            source=source, medium=medium, entity__in=entities
        ).values_list('entity', flat=True)

        subscribed_entities = Entity.objects.filter(
            Q(pk__in=group_subscribed_entities) | Q(pk__in=individual_subs),
            id__in=[e.id for e in entities]
        ).exclude(pk__in=relevant_unsubscribes)

        return subscribed_entities

    def _mediums_subscribed_individual(self, source, entity):
        """Return the mediums a single entity is subscribed to for a source.
        """
        super_entities = entity.super_relationships.all().values_list('super_entity')
        entity_is_subscribed = Q(subentity_type__isnull=True, entity=entity)
        super_entity_is_subscribed = Q(subentity_type=entity.entity_type, entity__in=super_entities)
        subscribed_mediums = self.filter(
            entity_is_subscribed | super_entity_is_subscribed, source=source
        ).select_related('medium').values_list('medium', flat=True)
        unsubscribed_mediums = Unsubscribe.objects.filter(
            entity=entity, source=source
        ).select_related('medium').values_list('medium', flat=True)
        return Medium.objects.filter(id__in=subscribed_mediums).exclude(id__in=unsubscribed_mediums)

    def _mediums_subscribed_group(self, source, entity, subentity_type):
        """Return all the mediums any subentity in a group is subscrbed to.
        """
        all_group_sub_entities = entity.sub_relationships.select_related('sub_entity').filter(
            sub_entity__entity_type=subentity_type
        ).values_list('sub_entity')
        related_super_entities = EntityRelationship.objects.filter(
            sub_entity__in=all_group_sub_entities
        ).values_list('super_entity')
        group_subscribed_mediums = self.filter(
            source=source, subentity_type=subentity_type, entity__in=related_super_entities
        ).select_related('medium').values_list('medium', flat=True)
        return Medium.objects.filter(id__in=group_subscribed_mediums)

    def _is_subscribed_individual(self, source, medium, entity):
        """Return true if an entity is subscribed to that source/medium combo.
        """
        super_entities = entity.super_relationships.all().values_list('super_entity')
        entity_is_subscribed = Q(subentity_type__isnull=True, entity=entity)
        super_entity_is_subscribed = Q(subentity_type=entity.entity_type, entity__in=super_entities)
        is_subscribed = self.filter(
            entity_is_subscribed | super_entity_is_subscribed,
            source=source,
            medium=medium,
        ).exists()
        unsubscribed = Unsubscribe.objects.filter(
            source=source,
            medium=medium,
            entity=entity
        ).exists()
        return is_subscribed and not unsubscribed

    def _is_subscribed_group(self, source, medium, entity, subentity_type):
        """Return true if any subentity is subscribed to that source & medium.
        """
        all_group_sub_entities = entity.sub_relationships.select_related('sub_entity').filter(
            sub_entity__entity_type=subentity_type
        ).values_list('sub_entity')
        related_super_entities = EntityRelationship.objects.filter(
            sub_entity__in=all_group_sub_entities,
        ).values_list('super_entity')
        is_subscribed = self.filter(
            source=source,
            medium=medium,
            subentity_type=subentity_type,
            entity__in=related_super_entities
        ).exists()
        return is_subscribed


class Subscription(models.Model):
    """Include groups of entities to subscriptions.

    It is recommended that these be largely pre-configured within an
    application, as catch-all groups. The finer grained control of
    individual users subscription status is defined within the
    `Unsubscribe` model.

    If, however, you want to subscribe an individual entity to a
    source/medium combination, setting the `subentity_type` field to
    None will create an individual subscription.
    """
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')
    entity = models.ForeignKey(Entity)
    subentity_type = models.ForeignKey(ContentType, null=True)

    objects = SubscriptionManager()

    def __unicode__(self):
        s = "{entity} to {source} by {medium}"
        entity = self.entity.__unicode__()
        source = self.source.__unicode__()
        medium = self.medium.__unicode__()
        return s.format(entity=entity, source=source, medium=medium)


class UnsubscribeManager(models.Manager):
    def is_unsubscribed(self, source, medium, entity):
        """Return True if the entity is unsubscribed
        """
        return self.filter(source=source, medium=medium, entity=entity).exists()


class Unsubscribe(models.Model):
    """Individual entity-level unsubscriptions.

    Entities can opt-out individually from recieving any notification
    of a given source/medium combination.
    """
    entity = models.ForeignKey(Entity)
    medium = models.ForeignKey('Medium')
    source = models.ForeignKey('Source')

    objects = UnsubscribeManager()

    def __unicode__(self):
        s = "{entity} from {source} by {medium}"
        entity = self.entity.__unicode__()
        source = self.source.__unicode__()
        medium = self.medium.__unicode__()
        return s.format(entity=entity, source=source, medium=medium)


class NotificationQuerySet(models.query.QuerySet):
    def medium(self, medium, include_seen=True):
        """Return notifications for a given medium.

        Args:

          medium - A medium object to check for.

          include_seen (Optional) - If `False`, exclude all
          notification that have already been marked as seen.

        Returns:

          A QuerySet that filters out all notifications that are not
          for the given medium. Can additionally filter out
          notifications that have already been seen.
        """
        if include_seen:
            notifications_for_medium = NotificationMedium.objects.filter(
                medium=medium,
            ).values_list('notification')
        else:
            notifications_for_medium = NotificationMedium.objects.filter(
                medium=medium,
                time_seen__isnull=True,
            ).values_list('notification')
        return self.filter(id__in=notifications_for_medium)

    def mark_seen(self, for_medium):
        """Set `time_seen` on the selected notifications for the medium.

        If there are any notifications that already have a `time_seen`
        their values will not be updated.

        Args:

          for_medium - A medium object to update `time_seen` objects
          for.

        Returns:

           The number of objects that are marked as seen.

        """
        time = datetime.datetime.utcnow()
        updated = NotificationMedium.objects.filter(
            notification__in=self,
            medium=for_medium,
            time_seen__isnull=True,
        ).update(time_seen=time)
        return updated


class NotificationManager(models.Manager):
    def get_queryset(self):
        return NotificationQuerySet(self.model)

    def medium(self, *args, **kwargs):
        return self.get_queryset().medium(*args, **kwargs)

    def mark_seen(self, *args, **kwargs):
        return self.get_queryset().mark_seen(*args, **kwargs)

    def create_notification(
            self, entity, notification_source, context,
            mediums=None, expires=None, subentity_type=None, uuid=None):
        """Create notifications, if the appropriate subscription exits.

        This method also creates the appropriate NotificationMedium
        records, which identify how the notification is to be
        delivered to the user. By default, NotificationMedium records
        are created for each medium the entity is subscribed to.

        Args:

          entity - The entity to be notified.

          notification_source - A source object for the notification.

          context - A python dictionary of information describing the
          notification. This is the context that will be used to
          render the notification when it is delieverd to the user.

          mediums (Optional) - If provided, restricts notifications to
          be created for the mediums given. If there are no
          subscriptions for those mediums, no notification will be created.

          expires (Optional) - A datetime or timedelta that signifies
          when the notification is no longer relevant. It is used to
          set the `time_expires` field on the notification. If a
          timedelta is given, the `time_expires` field will be set to
          the current time plus the timedelta.

          subentity_type (Optional) - A content type. If
          subentity_type is not `None` it signifies that this is a
          notification for a group. This field then describes the type
          of sub-entity of the given entity that are in the group to
          be notified.

          uuid (Optional) - A string that uniquely identifies the
          notification. If not given, one will be created. If the uuid
          is not unique, an error will be raised.

        Returns:

          The notification object created. If no subscriptions exist
          for the notification, returns None.

        Raises:

          IntegrityError - raised if the provided uuid already exists
          in a Notification.
        """
        # First we check if there are any mediums subscribed. If not,
        # we simply return.
        mediums_subscribed = Subscription.objects.mediums_subscribed(
            source=notification_source,
            entity=entity,
            subentity_type=subentity_type
        )
        if mediums is None:
            mediums = mediums_subscribed
        else:
            mediums = mediums_subscribed.filter(id__in=(m.id for m in mediums))
        if not mediums.exists():
            return None

        # Then, if there is at least one medium, we create the base
        # notification object.
        current_time = datetime.datetime.utcnow()
        if isinstance(expires, timedelta):
            expires = current_time + expires
        if not uuid:
            uuid = '{source}-{timestamp}'.format(
                source=notification_source.name,
                timestamp=current_time.strftime('%Y.%d.%m.%H.%M.%S.%f')
            )
        notification = self.create(
            entity=entity,
            subentity_type=subentity_type,
            source=notification_source,
            context=context,
            time_sent=current_time,
            time_expires=expires,
            uuid=uuid,
        )

        # Then we create all the related medium objects.
        NotificationMedium.objects.bulk_create(
            NotificationMedium(notification=notification, medium=medium)
            for medium in mediums
        )
        return notification


class Notification(models.Model):
    entity = models.ForeignKey(Entity)
    subentity_type = models.ForeignKey(ContentType, null=True)
    source = models.ForeignKey(Source)
    context = jsonfield.JSONField()
    time_sent = models.DateTimeField()
    time_expires = models.DateTimeField(null=True, default=None)
    uuid = models.CharField(max_length=128, unique=True)

    objects = NotificationManager()


class NotificationMedium(models.Model):
    notification = models.ForeignKey('Notification')
    medium = models.ForeignKey(Medium)
    time_seen = models.DateTimeField(null=True, default=None)
