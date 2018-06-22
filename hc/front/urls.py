from django.conf.urls import include, url

from hc.front import views

check_urls = [
    url(r'^name/$', views.update_name, name="hc-update-name"),
    url(r'^priority/$', views.update_priority, name="hc-update-priority"),
    url(r'^escalations/$', views.update_escalation, name="hc-update-escalation"),
    url(r'^timeout/$', views.update_timeout, name="hc-update-timeout"),
    url(r'^pause/$', views.pause, name="hc-pause"),
    url(r'^remove/$', views.remove_check, name="hc-remove-check"),
    url(r'^log/$', views.log, name="hc-log"),
]

channel_urls = [
    url(r'^$', views.channels, name="hc-channels"),
    url(r'^add/$', views.add_channel, name="hc-add-channel"),
    url(r'^add_email/$', views.add_email, name="hc-add-email"),
    url(r'^add_webhook/$', views.add_webhook, name="hc-add-webhook"),
    url(r'^add_pd/$', views.add_pd, name="hc-add-pd"),
    url(r'^add_slack/$', views.add_slack, name="hc-add-slack"),
    url(r'^add_slack_btn/$', views.add_slack_btn, name="hc-add-slack-btn"),
    url(r'^add_hipchat/$', views.add_hipchat, name="hc-add-hipchat"),
    url(r'^add_pushbullet/$', views.add_pushbullet, name="hc-add-pushbullet"),
    url(r'^add_pushover/$', views.add_pushover, name="hc-add-pushover"),
    url(r'^add_victorops/$', views.add_victorops, name="hc-add-victorops"),
    url(r'^([\w-]+)/checks/$', views.channel_checks, name="hc-channel-checks"),
    url(r'^([\w-]+)/remove/$', views.remove_channel, name="hc-remove-channel"),
    url(r'^([\w-]+)/verify/([\w-]+)/$', views.verify_email,
        name="hc-verify-email"),
]

blog_urls = [

    url(r'^add/$', views.add_blog, name="hc-add-blog"),
    url(r'^create/$', views.create_blogpost, name="hc-create-blogpost"),
    url(r'^category/$', views.add_category, name="hc-add-category"),
    url(r'^(?P<id>\d+)$', views.read_blogpost, name="hc-read-blogpost"),
    url(r'^remove/(?P<id>\d+)$', views.remove_blogpost, name="hc-remove-blogpost"),
    url(r'^edit/(?P<id>\d+)$', views.edit_blogpost, name="hc-edit-blogpost"),
]
urlpatterns = [
    url(r'^$', views.index, name="hc-index"),
    url(r'^checks/$', views.my_checks, name="hc-checks"),
    url(r'^checks/add/$', views.add_check, name="hc-add-check"),
    url(r'^checks/platforms/$', views.checks_platforms, name="hc-platforms"),
    url(r'^checks/platforms/github/$', views.check_github, name="hc-platforms-github"),
    url(r'^checks/platforms/github/integrate$', views.create_github_webhook, name="hc-integrate-github"),
    url(r'^checks/platforms/github/repos$', views.github_repos, name="hc-github-repos"),    
    url(r'^checks/([\w-]+)/', include(check_urls)),
    url(r'^integrations/', include(channel_urls)),
    url(r'^issues/', views.unresolved_issues, name="issues"),

    url(r'^docs/$', views.docs, name="hc-docs"),
    url(r'^docs/api/$', views.docs_api, name="hc-docs-api"),
    url(r'^about/$', views.about, name="hc-about"),
    url(r'^tasks/$', views.tasks, name="hc-tasks"),
    url(r'^tasks/sendemail/$', views.send_email, name="hc-send-email"),
    url(r'^tasks/backup/$', views.backup, name="hc-back-up"),
    url(r'^faq/$', views.faq, name="hc-faq"),
    url(r'^privacy/$', views.privacy, name="hc-privacy"),
    url(r'^terms/$', views.terms, name="hc-terms"),

    url(r'^blog/$', views.blog, name="hc-blog"),
    url(r'^blog/', include(blog_urls)),
]
