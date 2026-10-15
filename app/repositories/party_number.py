import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.party_number_counter import PartyNumberCounter


async def next_number(db: AsyncSession, owner_id: uuid.UUID, party_type: str) -> int:
    statement = (
        insert(PartyNumberCounter)
        .values(owner_id=owner_id, party_type=party_type, last_number=1)
        .on_conflict_do_update(
            index_elements=[PartyNumberCounter.owner_id, PartyNumberCounter.party_type],
            set_={"last_number": PartyNumberCounter.last_number + 1},
        )
        .returning(PartyNumberCounter.last_number)
    )
    result = await db.execute(statement)
    return result.scalar_one()
