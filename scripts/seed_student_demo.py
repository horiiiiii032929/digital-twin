"""Seed the ignored local SQLite store with the synthetic student demo fixture."""

from services.api.app.store import student_store
from src.digital_twin.student import seed_synthetic_student_workflow


def main() -> None:
    fixture = seed_synthetic_student_workflow(student_store)
    print(
        "Seeded synthetic student demo: "
        f"account={fixture.student_a_id} course={fixture.course_a_id} "
        f"release={fixture.release_a_id}"
    )


if __name__ == "__main__":
    main()
