class DatabaseRouter:
    """
    A router to control all database operations on models in
    the `admin_hub` application.
    """

    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'admin_hub':
            return 'tcpl_admin_db'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'admin_hub':
            return 'tcpl_admin_db'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        if obj1._state.db == 'admin_hub' or obj2._state.db == 'admin_hub':
            return obj1._state.db == obj2._state.db
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'admin_hub':
            return db == 'tcpl_admin_db'
        return db == 'default'
