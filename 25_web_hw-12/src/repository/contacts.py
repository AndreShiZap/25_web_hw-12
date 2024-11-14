from datetime import date, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Contact, User
from src.schemas.contact import ContactSchema


async def get_contacts(limit: int, offset: int, db: AsyncSession, user: User):
    stmt = select(Contact).filter_by(user=user).offset(offset).limit(limit)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_contact(contact_id: int, db: AsyncSession, user: User):
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    return contact.scalar_one_or_none()


async def create_contact(body: ContactSchema, db: AsyncSession, user: User):
    contact = Contact(**body.model_dump(exclude_unset=True), user=user)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


async def update_contact(contact_id: int, body: ContactSchema, db: AsyncSession, user: User):
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        contact.first_name = body.first_name
        contact.last_name = body.last_name
        contact.email = body.email
        contact.phone = body.phone
        contact.birthday = body.birthday
        contact.data_add = body.data_add
        await db.commit()
        await db.refresh(contact)
    return contact


async def delete_contact(contact_id: int, db: AsyncSession, user: User):
    stmt = select(Contact).filter_by(id=contact_id, user=user)
    contact = await db.execute(stmt)
    contact = contact.scalar_one_or_none()
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact


async def search_contacts(db: AsyncSession, user: User, first_name: Optional[str] = None, last_name: Optional[str] = None,
                          email: Optional[str] = None) -> List[Contact]:
    stmt = select(Contact).filter_by(user=user)
    if first_name:
        stmt = stmt.filter(Contact.first_name.ilike(f"%{first_name}%"))
    if last_name:
        stmt = stmt.filter(Contact.last_name.ilike(f"%{last_name}%"))
    if email:
        stmt = stmt.filter(Contact.email.ilike(f"%{email}%"))
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_upcoming_birthdays(db: AsyncSession, user: User, days: int = 7):
    today = date.today()
    upcoming_contacts = []

    stmt = select(Contact).filter_by(user=user)
    contacts = await db.execute(stmt)

    contacts = contacts.scalars().all()

    for contact in contacts:
        birthday_real = contact.birthday
        birthday_this_year = birthday_real.replace(year=today.year)
        if birthday_this_year < today:
            birthday_this_year = birthday_real.replace(year=today.year + 1)

        days_until_birthday = (birthday_this_year - today).days
        if 0 <= days_until_birthday <= days:
            congratulation_date = adjust_for_weekend(birthday_this_year)
            congratulation_date_str = date_to_string(congratulation_date)
            upcoming_contacts.append({
                "contact_id": contact.id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "congratulation_date": congratulation_date_str
            })

    return upcoming_contacts


def date_to_string(date):
    return date.strftime("%d.%m.%Y")


def adjust_for_weekend(birthday):
    if birthday.weekday() >= 5:
        return find_next_weekday(birthday, 0)
    return birthday


def find_next_weekday(start_date, weekday):
    days_ahead = weekday - start_date.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return start_date + timedelta(days=days_ahead)
