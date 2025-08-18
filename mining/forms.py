from django import forms
from .models import Dataset

class DatasetUploadForm(forms.ModelForm):
    """Form for uploading datasets"""
    
    class Meta:
        model = Dataset
        fields = ['file', 'name', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
        
    def clean_file(self):
        """Validate file format"""
        file = self.cleaned_data.get('file', False)
        if file:
            if file.size > 100 * 1024 * 1024:  # 100MB
                raise forms.ValidationError("File size cannot exceed 100MB")
            
            ext = file.name.split('.')[-1].lower()
            if ext not in ['csv', 'xlsx', 'xls']:
                raise forms.ValidationError("Only CSV and Excel files are supported")
                
        return file 