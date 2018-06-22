from django import forms
from hc.api.models import Channel


class NameTagsForm(forms.Form):
    name = forms.CharField(max_length=100, required=False)
    tags = forms.CharField(max_length=500, required=False)

    def clean_tags(self):
        l = []

        for part in self.cleaned_data["tags"].split(" "):
            part = part.strip()
            if part != "":
                l.append(part)

        return " ".join(l)


class TimeoutForm(forms.Form):

    timeout = forms.IntegerField(min_value=60)
    grace = forms.IntegerField(min_value=60)
    nag = forms.IntegerField(min_value=60)

class EscalationForm(forms.Form):

    escalation_list = forms.CharField()
    escalation_interval = forms.IntegerField(min_value=60)
    

class PriorityForm(forms.Form):
    priority = forms.IntegerField(required=True)


class AddChannelForm(forms.ModelForm):

    class Meta:
        model = Channel
        fields = ['kind', 'value']

    def clean_value(self):
        value = self.cleaned_data["value"]
        return value.strip()


class AddWebhookForm(forms.Form):
    error_css_class = "has-error"

    value_down = forms.URLField(max_length=1000, required=False)
    value_up = forms.URLField(max_length=1000, required=False)

    def get_value(self):
        return "{value_down}\n{value_up}".format(**self.cleaned_data)

class AddGitWebhookForm(forms.Form):
    repo_name = forms.CharField(required=True)

class EmailTaskForm(forms.Form):

    recipient_email = forms.EmailField(required=True)
    email_subject = forms.CharField(required=True)
    email_body= forms.CharField(required=False)

class BackupTaskForm(forms.Form):

    file_name = forms.CharField(required=True)
    check_name = forms.CharField(required=True)


class BlogForm(forms.Form):
    title = forms.CharField(required=True)
    category = forms.CharField(required=True)
    content = forms.CharField(required=True)

class BlogCategoriesForm(forms.Form):
    category = forms.CharField(required=True)

