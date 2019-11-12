from django.urls import include, re_path
from django.contrib import admin
from django.views.generic.base import RedirectView


urlpatterns = [
    # Examples:
    re_path(r'^$', RedirectView.as_view(url="appliances/", permanent=False),
            name='home'),
    # url(r'^blog/', include('blog.urls')),
    re_path(r'^appliances/', include('appliances.urls')),
    re_path(r'^admin/', admin.site.urls),
]
