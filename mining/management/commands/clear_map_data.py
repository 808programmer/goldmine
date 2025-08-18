from django.core.management.base import BaseCommand
from mining.models import (
    PredictionHistory, 
    GeologicalFeature, 
    MineralDeposit, 
    SoilAnalysis, 
    PDFTextData, 
    Dataset,
    GeologicalSurvey
)

class Command(BaseCommand):
    help = 'Clear all data that generates points on the map visualization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to delete all map data (required for actual deletion)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting anything',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        confirm = options['confirm']
        
        if not dry_run and not confirm:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  WARNING: This will permanently delete all map data!\n'
                    'To proceed, run with --confirm flag\n'
                    'To see what would be deleted without actually deleting, run with --dry-run'
                )
            )
            return
        
        self.stdout.write("=" * 60)
        self.stdout.write("MAP DATA CLEARANCE COMMAND")
        self.stdout.write("=" * 60)
        
        if dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No data will be actually deleted")
            self.stdout.write("")
        
        # 1. Clear PredictionHistory (Manual gold predictions)
        prediction_count = PredictionHistory.objects.count()
        self.stdout.write(f"📊 PredictionHistory records: {prediction_count}")
        if not dry_run and prediction_count > 0:
            PredictionHistory.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {prediction_count} prediction records")
            )
        
        # 2. Clear MineralDeposit records
        mineral_count = MineralDeposit.objects.count()
        self.stdout.write(f"💎 MineralDeposit records: {mineral_count}")
        if not dry_run and mineral_count > 0:
            MineralDeposit.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {mineral_count} mineral deposit records")
            )
        
        # 3. Clear SoilAnalysis records
        soil_count = SoilAnalysis.objects.count()
        self.stdout.write(f"🌱 SoilAnalysis records: {soil_count}")
        if not dry_run and soil_count > 0:
            SoilAnalysis.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {soil_count} soil analysis records")
            )
        
        # 4. Clear GeologicalFeature records (Survey data and intelligent coordinates)
        feature_count = GeologicalFeature.objects.count()
        self.stdout.write(f"🗺️  GeologicalFeature records: {feature_count}")
        
        # Show breakdown of feature types
        if feature_count > 0:
            feature_types = GeologicalFeature.objects.values_list('feature_type', flat=True).distinct()
            self.stdout.write(f"   Feature types found: {list(feature_types)}")
            
            # Count intelligent features specifically
            intelligent_count = GeologicalFeature.objects.filter(
                feature_type__icontains='intelligent'
            ).count()
            self.stdout.write(f"   Intelligent coordinates: {intelligent_count}")
            
            if not dry_run:
                GeologicalFeature.objects.all().delete()
                self.stdout.write(
                    self.style.SUCCESS(f"   ✅ Deleted {feature_count} geological feature records")
                )
        
        # 5. Clear PDFTextData records
        pdf_count = PDFTextData.objects.count()
        self.stdout.write(f"📄 PDFTextData records: {pdf_count}")
        if not dry_run and pdf_count > 0:
            PDFTextData.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {pdf_count} PDF text data records")
            )
        
        # 6. Clear Dataset records
        dataset_count = Dataset.objects.count()
        self.stdout.write(f"📁 Dataset records: {dataset_count}")
        if not dry_run and dataset_count > 0:
            Dataset.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {dataset_count} dataset records")
            )
        
        # 7. Clear GeologicalSurvey records
        survey_count = GeologicalSurvey.objects.count()
        self.stdout.write(f"🔬 GeologicalSurvey records: {survey_count}")
        if not dry_run and survey_count > 0:
            GeologicalSurvey.objects.all().delete()
            self.stdout.write(
                self.style.SUCCESS(f"   ✅ Deleted {survey_count} geological survey records")
            )
        
        self.stdout.write("")
        self.stdout.write("=" * 60)
        
        if dry_run:
            total_records = (prediction_count + mineral_count + soil_count + 
                            feature_count + pdf_count + dataset_count + survey_count)
            self.stdout.write(f"🔍 DRY RUN SUMMARY: {total_records} total records would be deleted")
            self.stdout.write("Run with --confirm to actually delete the data")
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ MAP DATA CLEARANCE COMPLETED")
            )
            self.stdout.write("All map data has been cleared. The map should now be empty.")
        
        self.stdout.write("=" * 60) 