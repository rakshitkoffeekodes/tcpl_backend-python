from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg import openapi

class CustomSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        if schema and isinstance(schema, openapi.Swagger):
            schema.schemes = ["https", "http"]
        return schema
