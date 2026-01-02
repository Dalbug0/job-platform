#!/usr/bin/env python3
"""
Скрипт для запуска интеграционных тестов job-platform.

Запуск: python run_integration_tests.py
"""
"""
Скрипт для запуска интеграционных тестов job-platform.

Этот скрипт:
1. Запускает изолированное тестовое окружение (docker-compose.test.yml)
2. Ожидает готовности всех сервисов
3. Запускает интеграционные тесты в каждом git submodule
4. Останавливает тестовое окружение
5. Показывает результаты тестирования

Использование:
    python run_integration_tests.py [--no-cleanup] [--verbose]

Аргументы:
    --no-cleanup    Не останавливать контейнеры после тестов
    --verbose, -v   Подробный вывод
"""

import argparse
import subprocess
import sys
import time
import os
from pathlib import Path
import requests
from typing import List, Dict, Tuple


class IntegrationTestRunner:
    """Класс для управления интеграционными тестами"""

    def __init__(self, verbose: bool = False, no_cleanup: bool = False):
        self.verbose = verbose
        self.no_cleanup = no_cleanup
        self.project_root = Path(__file__).parent
        self.test_results: List[Dict] = []

    def log(self, message: str, level: str = "INFO"):
        """Логирование с уровнями"""
        if self.verbose or level in ["ERROR", "WARNING", "SUCCESS"]:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")

    def check_dependencies(self) -> bool:
        """Проверка зависимостей"""
        self.log("Проверка зависимостей...")

        # Проверка Docker
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"[OK] Docker: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[ERROR] Docker не установлен или не запущен", "ERROR")
            return False

        # Проверка docker-compose
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"[OK] Docker Compose: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("[ERROR] Docker Compose не установлен", "ERROR")
            return False

        # Проверка Python
        try:
            result = subprocess.run(
                [sys.executable, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.log(f"[OK] Python: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.log("[ERROR] Python не найден", "ERROR")
            return False

        return True

    def check_env_files(self) -> bool:
        """Проверка наличия необходимых файлов окружения"""
        self.log("Проверка файлов окружения...")

        required_files = [
            self.project_root / ".env.dev",
            self.project_root / ".env.hh.dev"
        ]

        missing_files = []
        for env_file in required_files:
            if not env_file.exists():
                missing_files.append(env_file.name)

        if missing_files:
            self.log(f"[ERROR] Отсутствуют файлы окружения: {', '.join(missing_files)}", "ERROR")
            self.log("  Создайте их на основе примеров или получите от администратора проекта", "ERROR")
            return False

        self.log("[OK] Файлы окружения найдены")
        return True

    def start_test_environment(self) -> bool:
        """Запуск тестового окружения"""
        self.log("Запуск тестового окружения...")

        try:
            # Останавливаем и удаляем предыдущие контейнеры
            self.log("Очистка предыдущих контейнеров...")
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "down", "-v", "--remove-orphans"],
                check=True,
                capture_output=not self.verbose,
                text=True,
                cwd=self.project_root
            )

            # Запускаем тестовое окружение
            self.log("Запуск сервисов...")
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "up", "-d"],
                check=True,
                capture_output=not self.verbose,
                text=True,
                cwd=self.project_root
            )

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] Ошибка запуска docker-compose: {e}", "ERROR")
            if not self.verbose and e.stderr:
                self.log(f"Stderr: {e.stderr}", "ERROR")
            return False

        return True

    def wait_for_services(self, timeout: int = 300) -> bool:
        """Ожидание готовности сервисов"""
        self.log(f"Ожидание готовности сервисов (таймаут: {timeout}с)...")

        services = {
            "test_db": {
                "url": "http://localhost:5433",  # Проверяем через API
                "name": "База данных",
                "check_function": self._check_database
            },
            "test_api": {
                "url": "http://localhost:8001/api/v1/docs",
                "name": "API",
                "check_function": self._check_api
            }
        }

        start_time = time.time()

        for service_name, service_info in services.items():
            self.log(f"  Ожидание {service_info['name']}...")
            service_ready = False
            attempts = 0

            while time.time() - start_time < timeout and not service_ready:
                attempts += 1
                try:
                    if service_info["check_function"](service_info["url"]):
                        service_ready = True
                        self.log(f"  [OK] {service_info['name']} готов (попытка {attempts})")
                    else:
                        time.sleep(5)
                except Exception as e:
                    if self.verbose:
                        self.log(f"  Попытка {attempts} для {service_info['name']} не удалась: {e}")
                    time.sleep(5)

            if not service_ready:
                self.log(f"[ERROR] {service_info['name']} не готов за {timeout} секунд", "ERROR")
                self._show_container_logs()
                return False

        self.log("[OK] Все сервисы готовы!")
        return True

    def _check_database(self, url: str) -> bool:
        """Проверка готовности базы данных"""
        # Проверяем напрямую через pg_isready
        try:
            result = subprocess.run([
                "docker", "exec", "job_platform_test_db",
                "pg_isready", "-U", "test_user", "-d", "job_platform_test"
            ], capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            return False

    def _check_api(self, url: str) -> bool:
        """Проверка готовности API"""
        try:
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False

    def run_submodule_tests(self) -> List[Dict]:
        """Запуск тестов в git submodules"""
        self.log("Запуск интеграционных тестов...")

        submodules = [
            # TODO: Добавить job_aggregator после настройки интеграционных тестов
            # {
            #     "name": "job_aggregator",
            #     "path": self.project_root / "job_aggregator",
            #     "test_command": ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
            #     "env": {
            #         "API_BASE_URL": "http://localhost:8001",
            #         "POSTGRES_HOST": "localhost",
            #         "POSTGRES_PORT": "5433",
            #         "POSTGRES_USER": "test_user",
            #         "POSTGRES_PASSWORD": "test_pass",
            #         "POSTGRES_DB": "job_platform_test"
            #     }
            # },
            {
                "name": "job-bot",
                "path": self.project_root / "job-bot",
                "test_command": ["python", "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
                "env": {
                    "API_BASE_URL": "http://localhost:8001"
                }
            }
        ]

        results = []

        for submodule in submodules:
            self.log(f"Запуск тестов для {submodule['name']}...")
            result = self._run_single_test(submodule)
            results.append(result)

        return results

    def _run_single_test(self, submodule: Dict) -> Dict:
        """Запуск тестов для одного submodule"""
        result = {
            "name": submodule["name"],
            "success": False,
            "output": "",
            "error": ""
        }

        try:
            # Устанавливаем переменные окружения
            env = os.environ.copy()
            env.update(submodule["env"])

            # Запускаем тесты
            process = subprocess.run(
                submodule["test_command"],
                cwd=submodule["path"],
                env=env,
                capture_output=True,
                text=True,
                timeout=600  # 10 минут на модуль
            )

            result["success"] = process.returncode == 0
            result["output"] = process.stdout
            result["error"] = process.stderr

            if result["success"]:
                self.log(f"[SUCCESS] Тесты {submodule['name']} пройдены", "SUCCESS")
            else:
                self.log(f"[ERROR] Тесты {submodule['name']} провалились", "ERROR")
                if not self.verbose:
                    # Показываем последние строки вывода при ошибке
                    lines = (process.stdout + process.stderr).split('\n')[-20:]
                    self.log("Последние строки вывода:", "ERROR")
                    for line in lines:
                        if line.strip():
                            self.log(f"  {line}", "ERROR")

        except subprocess.TimeoutExpired:
            result["error"] = "Тесты превысили время ожидания (10 мин)"
            self.log(f"✗ Таймаут выполнения тестов {submodule['name']}", "ERROR")
        except Exception as e:
            result["error"] = str(e)
            self.log(f"✗ Ошибка запуска тестов {submodule['name']}: {e}", "ERROR")

        return result

    def cleanup_environment(self) -> bool:
        """Очистка тестового окружения"""
        if self.no_cleanup:
            self.log("Пропуск очистки (--no-cleanup)")
            return True

        self.log("Очистка тестового окружения...")

        try:
            subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "down", "-v"],
                check=True,
                capture_output=not self.verbose,
                text=True,
                cwd=self.project_root
            )
            self.log("[OK] Тестовое окружение очищено")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] Ошибка очистки: {e}", "ERROR")
            return False

    def _show_container_logs(self):
        """Показать логи контейнеров при ошибке"""
        self.log("Показываем логи контейнеров для диагностики...", "WARNING")
        try:
            result = subprocess.run(
                ["docker-compose", "-f", "docker-compose.test.yml", "logs"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            self.log("Логи контейнеров:", "WARNING")
            self.log(result.stdout, "WARNING")
            if result.stderr:
                self.log("Ошибки:", "ERROR")
                self.log(result.stderr, "ERROR")
        except Exception as e:
            self.log(f"Не удалось получить логи: {e}", "ERROR")

    def print_summary(self, results: List[Dict]):
        """Вывод итогового отчета"""
        print("\n" + "="*60)
        print("РЕЗУЛЬТАТЫ ИНТЕГРАЦИОННЫХ ТЕСТОВ")
        print("="*60)

        total_passed = 0
        total_failed = 0

        for result in results:
            status = "ПРОЙДЕН" if result["success"] else "ПРОВАЛЕН"
            print(f"\n{result['name']}: {status}")

            if not result["success"] and result["error"]:
                print(f"  Ошибка: {result['error']}")

            if result["success"]:
                total_passed += 1
            else:
                total_failed += 1

        print(f"\n{'='*60}")
        print(f"ИТОГО: {total_passed + total_failed} модулей")
        print(f"Пройдено: {total_passed}")
        print(f"Провалено: {total_failed}")

        if total_failed == 0:
            print("\nВСЕ ИНТЕГРАЦИОННЫЕ ТЕСТЫ ПРОЙДЕНЫ!")
            return True
        else:
            print(f"\n{total_failed} модуль(ей) провалено")
            return False

    def run(self) -> bool:
        """Основной метод запуска"""
        print("Запуск интеграционных тестов job-platform")
        print("="*60)

        # Проверки
        if not self.check_dependencies():
            return False

        if not self.check_env_files():
            return False

        # Запуск окружения
        if not self.start_test_environment():
            return False

        # Ожидание сервисов
        if not self.wait_for_services(180):  # 3 минуты вместо 5
            self.cleanup_environment()
            return False

        # Запуск тестов
        results = self.run_submodule_tests()

        # Очистка
        cleanup_success = self.cleanup_environment()

        # Итоги
        success = self.print_summary(results)

        # Финальный статус
        if success and cleanup_success:
            print("\nИНТЕГРАЦИОННЫЕ ТЕСТЫ ЗАВЕРШЕНЫ УСПЕШНО")
            return True
        else:
            print("\nИНТЕГРАЦИОННЫЕ ТЕСТЫ ЗАВЕРШЕНЫ С ОШИБКАМИ")
            return False


def main():
    """Точка входа"""
    parser = argparse.ArgumentParser(description="Запуск интеграционных тестов job-platform")
    parser.add_argument("--no-cleanup", action="store_true",
                       help="Не останавливать контейнеры после тестов")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Подробный вывод")

    args = parser.parse_args()

    runner = IntegrationTestRunner(verbose=args.verbose, no_cleanup=args.no_cleanup)
    success = runner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()