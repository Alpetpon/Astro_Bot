import json
from sqlalchemy.orm import Session
from database import Course, Tariff, Lesson, get_db


class AdminPanel:
    """Утилиты для администрирования бота"""
    
    @staticmethod
    def create_sample_courses():
        """Создание примеров курсов для демонстрации"""
        db: Session = get_db()
        
        try:
            # Курс 1: LOVE-код
            love_course = Course(
                name="LOVE-код",
                slug="love-code",
                description="Глубокое погружение в астрологию отношений",
                short_description="Узнайте секреты гармоничных отношений через призму астрологии",
                program=json.dumps([
                    "Модуль 1: Венера и Марс в отношениях",
                    "Модуль 2: Синастрия партнеров",
                    "Модуль 3: Прогностика отношений",
                    "Модуль 4: Кармические связи"
                ]),
                duration="4 недели",
                is_active=True,
                order=1
            )
            db.add(love_course)
            db.flush()
            
            # Тарифы для LOVE-код
            love_tariff_basic = Tariff(
                course_id=love_course.id,
                name="Самостоятельное обучение",
                description="Доступ ко всем материалам курса",
                price=9900.0,
                with_support=False,
                features=json.dumps([
                    "Все видео-уроки",
                    "Конспекты и материалы",
                    "Доступ на 6 месяцев"
                ]),
                is_active=True,
                order=1
            )
            
            love_tariff_vip = Tariff(
                course_id=love_course.id,
                name="С сопровождением куратора",
                description="Все материалы + персональная поддержка",
                price=24900.0,
                with_support=True,
                features=json.dumps([
                    "Все видео-уроки",
                    "Конспекты и материалы",
                    "Личный куратор",
                    "Еженедельные групповые встречи",
                    "Разбор личной натальной карты",
                    "Доступ на 12 месяцев"
                ]),
                is_active=True,
                order=2
            )
            db.add_all([love_tariff_basic, love_tariff_vip])
            
            # Уроки для LOVE-код
            love_lessons = [
                Lesson(
                    course_id=love_course.id,
                    module_number=1,
                    lesson_number=1,
                    title="Введение в астрологию отношений",
                    description="Первый шаг в мир астропсихологии отношений",
                    content="В этом уроке мы познакомимся с основными понятиями...",
                    video_url="https://youtube.com/example1",
                    duration="45 минут",
                    order=1,
                    is_free=True
                ),
                Lesson(
                    course_id=love_course.id,
                    module_number=1,
                    lesson_number=2,
                    title="Венера в натальной карте",
                    description="Изучаем планету любви и привязанности",
                    content="Венера показывает, как мы любим и что ценим...",
                    video_url="https://youtube.com/example2",
                    materials=json.dumps([
                        "Таблица характеристик Венеры в знаках",
                        "Конспект урока в PDF"
                    ]),
                    duration="60 минут",
                    order=2
                ),
                Lesson(
                    course_id=love_course.id,
                    module_number=2,
                    lesson_number=1,
                    title="Основы синастрии",
                    description="Как анализировать совместимость партнеров",
                    content="Синастрия - это метод сравнения натальных карт...",
                    video_url="https://youtube.com/example3",
                    duration="50 минут",
                    order=3
                )
            ]
            db.add_all(love_lessons)
            
            # Курс 2: Основы астрологии
            astro_course = Course(
                name="Основы астрологии",
                slug="astro-basics",
                description="Полный базовый курс по астрологии для начинающих",
                short_description="Научитесь читать натальные карты с нуля",
                program=json.dumps([
                    "Модуль 1: Знаки Зодиака",
                    "Модуль 2: Планеты",
                    "Модуль 3: Дома гороскопа",
                    "Модуль 4: Аспекты",
                    "Модуль 5: Интерпретация карты"
                ]),
                duration="8 недель",
                is_active=True,
                order=2
            )
            db.add(astro_course)
            db.flush()
            
            # Тарифы для Основы астрологии
            astro_tariff_basic = Tariff(
                course_id=astro_course.id,
                name="Без сопровождения",
                description="Самостоятельное изучение материалов",
                price=14900.0,
                with_support=False,
                features=json.dumps([
                    "Все видео-уроки",
                    "Методические материалы",
                    "Практические задания",
                    "Доступ на 12 месяцев"
                ]),
                is_active=True,
                order=1
            )
            
            astro_tariff_vip = Tariff(
                course_id=astro_course.id,
                name="С сопровождением",
                description="Обучение с поддержкой наставника",
                price=34900.0,
                with_support=True,
                features=json.dumps([
                    "Все видео-уроки",
                    "Методические материалы",
                    "Практические задания",
                    "Проверка домашних заданий",
                    "Групповые разборы",
                    "Поддержка в чате",
                    "Сертификат об окончании",
                    "Доступ на 24 месяца"
                ]),
                is_active=True,
                order=2
            )
            db.add_all([astro_tariff_basic, astro_tariff_vip])
            
            # Уроки для Основы астрологии
            astro_lessons = [
                Lesson(
                    course_id=astro_course.id,
                    module_number=1,
                    lesson_number=1,
                    title="Что такое астрология?",
                    description="Введение в науку о звездах",
                    content="История астрологии и основные принципы...",
                    video_url="https://youtube.com/example4",
                    duration="40 минут",
                    order=1,
                    is_free=True
                ),
                Lesson(
                    course_id=astro_course.id,
                    module_number=1,
                    lesson_number=2,
                    title="Стихии и качества",
                    description="Базовая классификация знаков",
                    content="Огонь, Земля, Воздух, Вода...",
                    video_url="https://youtube.com/example5",
                    materials=json.dumps([
                        "Таблица стихий и качеств",
                        "Рабочая тетрадь"
                    ]),
                    duration="55 минут",
                    order=2
                )
            ]
            db.add_all(astro_lessons)
            
            db.commit()
            print("✅ Sample courses created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating courses: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    @staticmethod
    def list_courses():
        """Вывод списка курсов"""
        db: Session = get_db()
        
        try:
            courses = db.query(Course).all()
            
            if not courses:
                print("No courses found.")
                return
            
            for course in courses:
                print(f"\nCourse: {course.name} ({course.slug})")
                print(f"  Active: {course.is_active}")
                print(f"  Tariffs: {len(course.tariffs)}")
                print(f"  Lessons: {len(course.lessons)}")
        
        finally:
            db.close()


if __name__ == "__main__":
    # Создание примеров курсов
    AdminPanel.create_sample_courses()
    
    # Вывод списка курсов
    print("\n" + "="*50)
    AdminPanel.list_courses()

