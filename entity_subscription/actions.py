

class BaseAction(object):

    def __init__(self, notification):
        self.notification = notification

    def render(self, html=True):
        render_str = '{0} {1} {2} {3}'.format(
            self.get_actor_display(self.notification.actor, html=html),
            self.get_action_display(self.notification.action, html=html),
            self.get_action_object_display(self.notification.action_object, html=html),
            self.get_target_display(self.notification.target, html=html),
        )
        return render_str.strip()

    def get_actor_display(self, actor, html=True):
        if html:
            return '<a href="{0}">{1}</a>'.format(self.get_actor_url(), actor.entity)
        return actor.entity

    def get_action_display(self, action, html=True):
        return action.display_name

    def get_action_object_display(self, action_object, html=True):
        if not action_object:
            return ''
        if html:
            return '<a href="{0}">{1}</a>'.format(self.get_action_object_url(), action_object.entity)
        return action_object.entity

    def get_target_display(self, target, html=True):
        if not target:
            return ''
        if html:
            return 'to <a href="{0}">{1}</a>'.format(self.get_target_url(), target.entity)
        return 'to {0}'.format(target.entity)

    def get_actor_url(self):
        if self.notification.context:
            return self.notification.context.get('actor_url')

    def get_action_object_url(self):
        if self.notification.context:
            return self.notification.context.get('action_object_url')

    def get_target_url(self):
        if self.notification.context:
            return self.notification.context.get('target_url')
