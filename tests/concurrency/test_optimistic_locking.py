import concurrent.futures
from django.test import TransactionTestCase
from datetime import date
from django.db import connection
from apps.accounts.models import User
from apps.patients.models import Patient
from apps.patients.services import PatientService
from common.exceptions import OptimisticLockError


class OptimisticLockingConcurrencyTestCase(TransactionTestCase):
    """
    Automated concurrency test proving that optimistic locking prevents lost updates
    when multiple threads attempt to update the same resource concurrently.
    """
    def setUp(self):
        connection.close()
        self.user = User.objects.create_user(
            email="concurrent.user@example.com",
            name="Concurrent Tester",
            password="Password123!"
        )
        self.patient = PatientService.create_patient(
            user=self.user,
            data={
                "name": "Race Condition Patient",
                "date_of_birth": date(1988, 11, 20),
                "gender": "Non-binary"
            }
        )

    def test_concurrent_updates_prevent_lost_update(self):
        patient_id = self.patient.id
        initial_version = self.patient.version  # version = 1

        results = []
        errors = []

        def worker(worker_id):
            connection.close()  # Ensure each thread uses its own DB connection
            for attempt in range(5):
                try:
                    updated = PatientService.update_patient(
                        user=self.user,
                        patient_id=patient_id,
                        data={"name": f"Updated by worker {worker_id}"},
                        expected_version=initial_version  # Both workers compete using version 1
                    )
                    results.append(updated)
                    break
                except OptimisticLockError as exc:
                    errors.append(exc)
                    break
                except Exception as exc:
                    # Retry on SQLite transient table locks
                    if "locked" in str(exc).lower():
                        import time
                        time.sleep(0.05 * (attempt + 1))
                        continue
                    errors.append(exc)
                    break
            connection.close()

        # Run 2 concurrent worker threads competing to update version 1
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(worker, i) for i in range(1, 3)]
            concurrent.futures.wait(futures)

        self.assertEqual(len(results), 1, f"Expected 1 success, but got {len(results)}. Errors: {errors}")
        self.assertEqual(len(errors), 1, "The competing concurrent update must fail with OptimisticLockError")

        # The final persisted version in DB must be 2
        fresh_patient = Patient.objects.get(id=patient_id)
        self.assertEqual(fresh_patient.version, 2)
