from django import forms


class LowercaseEmailField(forms.EmailField):

    def clean(self, value):
        value = super(LowercaseEmailField, self).clean(value)
        return value.lower()


class EmailPasswordForm(forms.Form):
    email = LowercaseEmailField()
    password = forms.CharField(required=False)


class ReportSettingsForm(forms.Form):
    reports_allowed = forms.BooleanField(required=False)


class SetPasswordForm(forms.Form):
    password = forms.CharField()


class InviteTeamMemberForm(forms.Form):
    email = LowercaseEmailField()
    department = forms.CharField(required=False)
    check = forms.CharField()


class RemoveTeamMemberForm(forms.Form):
    email = LowercaseEmailField()


class TeamNameForm(forms.Form):
    team_name = forms.CharField(max_length=200, required=True)


class ReportsForm(forms.Form):
    reports_frequency = forms.CharField(required=True)


class UpdateTeamMemberPriority(forms.Form):
    email = LowercaseEmailField()


class AlertForm(forms.Form):
    alert_mode = forms.CharField(required=True)
    phone_number = forms.CharField(required=True)
