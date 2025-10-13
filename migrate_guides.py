"""
Скрипт для миграции гайдов из config.py в базу данных
"""
from database import init_db, get_db, Guide
from config import config


def migrate_guides():
    """Перенос гайдов из config.py в БД"""
    print("Инициализация базы данных...")
    init_db()
    
    db = get_db()
    
    try:
        # Проверяем, есть ли уже гайды в БД
        existing_count = db.query(Guide).count()
        if existing_count > 0:
            print(f"В базе уже есть {existing_count} гайдов.")
            response = input("Хотите продолжить миграцию? (yes/no): ")
            if response.lower() not in ['yes', 'y', 'да']:
                print("Миграция отменена.")
                return
        
        # Мигрируем гайды из config.GUIDES
        migrated = 0
        for index, guide_data in enumerate(config.GUIDES):
            # Проверяем, существует ли уже гайд с таким ID
            existing = db.query(Guide).filter(Guide.guide_id == guide_data['id']).first()
            if existing:
                print(f"Гайд '{guide_data['name']}' уже существует, пропускаем...")
                continue
            
            # Создаём новый гайд
            new_guide = Guide(
                guide_id=guide_data['id'],
                name=guide_data['name'],
                emoji=guide_data.get('emoji'),
                description=guide_data.get('description', ''),
                file_id=guide_data.get('file_id'),
                related_course_slug=guide_data.get('related_course_slug'),
                order=index,
                is_active=True
            )
            
            db.add(new_guide)
            migrated += 1
            print(f"✅ Добавлен гайд: {guide_data['name']}")
        
        db.commit()
        print(f"\n✅ Миграция завершена! Перенесено гайдов: {migrated}")
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == '__main__':
    migrate_guides()

