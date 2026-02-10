import os
import django
from django.apps import apps
from django.db import models
from django.utils.timezone import now

# Django設定の読み込み
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'groupf.settings')
django.setup()

def get_field_type_str(field):
    if isinstance(field, models.AutoField) or isinstance(field, models.BigAutoField):
        return "BigAuto" # or Auto
    if isinstance(field, models.CharField):
        return "Varchar"
    if isinstance(field, models.TextField):
        return "Text"
    if isinstance(field, models.IntegerField):
        return "Integer"
    if isinstance(field, models.BigIntegerField):
        return "BigInt"
    if isinstance(field, models.DateTimeField):
        return "DateTime"
    if isinstance(field, models.DateField):
        return "Date"
    if isinstance(field, models.BooleanField):
        return "Boolean"
    if isinstance(field, models.EmailField):
        return "Email"
    if isinstance(field, models.ForeignKey):
        return "BigInt" # FK is usually BigInt or Int
    if isinstance(field, models.OneToOneField):
        return "BigInt"
    if isinstance(field, models.ImageField):
        return "Image"
    if isinstance(field, models.FileField):
        return "File"
    return field.get_internal_type()

def get_default_value(field):
    if field.default == models.NOT_PROVIDED:
        return "-"
    if callable(field.default):
        if field.default == now: # 厳密には関数オブジェクト比較だが
            return "timezone.now"
        return "Callable"
    return str(field.default)

def is_pk_fk_nn(field):
    pk = "○" if field.primary_key else ""
    fk = "○" if field.is_relation and (isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField)) else ""
    nn = "○" if not field.null else "" # null=False -> NN=True
    return pk, fk, nn

print("=== Model Schema Inspection ===")

target_apps = [
    'accounts', 'tasks', 'manuals', 'consultations', 
    'schedule', 'interviews', 'notifications', 'chat',
    # 'team_tasks' は移行中とのことだが念のため出力してもよい
]

all_models_data = []

for app_config in apps.get_app_configs():
    if app_config.label not in target_apps:
        continue
        
    for model in app_config.get_models():
        model_name = model.__name__
        model_verbose_name = model._meta.verbose_name
        
        fields_data = []
        for field in model._meta.get_fields():
            if not isinstance(field, models.Field) or isinstance(field, models.ManyToManyRel) or isinstance(field, models.ManyToOneRel):
                continue
            
            # 論理名称
            logical_name = str(getattr(field, 'verbose_name', field.name))
            
            # 物理名称
            physical_name = field.name
            if isinstance(field, models.ForeignKey):
                physical_name += "_id"
            
            # データ型
            field_type = get_field_type_str(field)
            
            # 桁数
            length = getattr(field, 'max_length', "-")
            if length is None: length = "-"
            
            # 初期値
            default_val = get_default_value(field)
            
            # PK, FK, NN
            pk, fk, nn = is_pk_fk_nn(field)
            
            # 備考
            remarks = str(getattr(field, 'help_text', ""))
            if not remarks:
                if isinstance(field, models.ForeignKey):
                    remarks = "FK"
                elif field.unique:
                    remarks = "Unique"
                elif field.blank and field.null:
                    remarks = "Null可"

            fields_data.append({
                "logical_name": logical_name,
                "physical_name": physical_name,
                "type": field_type,
                "length": length,
                "default": default_val,
                "pk": pk,
                "fk": fk,
                "nn": nn,
                "remarks": remarks
            })

        all_models_data.append({
            "app": app_config.label,
            "model": model_name,
            "verbose_name": str(model_verbose_name),
            "fields": fields_data
        })

# JSONで出力して後続の処理で扱いやすくする（あるいは確認用）
import json
output_path = r'c:\Django課題制作 - コピー\groupf\models_schema.json'
try:
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_models_data, f, indent=2, ensure_ascii=False)
    print(f"Schema saved to {output_path}")
except Exception as e:
    print(f"Error saving schema: {e}")
