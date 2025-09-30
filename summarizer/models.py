from django.db import models

class EmailSummary(models.Model):
    email_file = models.FileField(upload_to='uploads')
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    def __str__(self):
        return f"Email Summary {self.id} - {self.created_at}"


class EmailResult(models.Model):
    email_summary = models.ForeignKey(EmailSummary,on_delete=models.CASCADE,related_name='results')
    sender = models.TextField()
    subject = models.TextField()
    summary = models.JSONField()

    def __str__(self):
        return f"{self.sender} - {self.subject}"