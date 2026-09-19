import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlmodel import Session, select  # noqa: E402

from app.db.models import Case, CaseStatus  # noqa: E402
from app.db.session import engine, init_db  # noqa: E402


def seed_demo_case() -> Case:
    """Initialize database and seed an initial investigation case."""
    print("Ensuring database tables are initialized...")
    init_db(engine)

    with Session(engine) as session:
        statement = select(Case).where(Case.name == "Operation Phantom Grid")
        existing_case = session.exec(statement).first()

        if existing_case:
            msg = (
                f"Demo case already exists: "
                f"[ID {existing_case.id}] {existing_case.name}"
            )
            print(msg)
            return existing_case

        demo_case = Case(
            name="Operation Phantom Grid",
            status=CaseStatus.ACTIVE.value,
        )
        session.add(demo_case)
        session.commit()
        session.refresh(demo_case)
        msg = (
            f"Successfully seeded demo case: [ID {demo_case.id}] "
            f"{demo_case.name} (Status: {demo_case.status})"
        )
        print(msg)
        return demo_case


if __name__ == "__main__":
    seed_demo_case()
