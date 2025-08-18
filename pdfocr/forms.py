from django import forms
from .models import PDFUpload

class PDFUploadForm(forms.ModelForm):
    class Meta:
        model = PDFUpload
        fields = ['pdf_file']
        widgets = {
            'pdf_file': forms.FileInput(attrs={
                'accept': '.pdf',
                'class': 'hidden',
                'id': 'pdf-file-input'
            })
        }
    
    def clean_pdf_file(self):
        pdf_file = self.cleaned_data.get('pdf_file')
        if pdf_file:
            if not pdf_file.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Only PDF files are allowed.")
            if pdf_file.size > 100 * 1024 * 1024:  # 100MB limit
                raise forms.ValidationError("File size cannot exceed 100MB.")
        return pdf_file
