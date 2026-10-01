import pytest

from bot.db.session import create_tables, make_engine, make_sessionmaker


@pytest.fixture
async def sessionmaker():
    engine = make_engine("sqlite+aiosqlite:///:memory:")
    await create_tables(engine)
    yield make_sessionmaker(engine)
    await engine.dispose()


@pytest.fixture
async def session(sessionmaker):
    async with sessionmaker() as s:
        yield s
