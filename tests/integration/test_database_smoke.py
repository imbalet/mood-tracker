import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_postgresql_is_available() -> None:
    database_url = os.environ["TEST_DATABASE_URL"]
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
            tables = await connection.execute(
                text("SELECT to_regclass('public.reference_states')")
            )
            assert tables.scalar_one() == "reference_states"
    finally:
        await engine.dispose()
