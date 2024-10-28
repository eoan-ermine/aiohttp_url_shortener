import uuid
import base62
from dataclasses import dataclass, asdict
import validators

import sqlalchemy as sa
from sqlalchemy import orm

import aiohttp_sqlalchemy as ahsa

metadata = sa.MetaData()
Base = orm.declarative_base(metadata=metadata)


async def init_db(app):
  ahsa.setup(app, [
    ahsa.bind('sqlite+aiosqlite:///database.sqlite'),
  ])
  await ahsa.init_db(app, metadata)


@dataclass
class Url(Base):
  __tablename__ = "url"

  url = sa.Column(sa.Text)
  short_code = sa.Column(sa.Text)
  secret = sa.Column(sa.Uuid, primary_key=True)

  def dict(self):
    return {"url": self.url, "short_code": self.short_code, "secret": str(self.secret)}

  @staticmethod
  async def create(url, session):
    if not validators.url(url):
      raise ValueError("URL validation error")
    new_url = Url(url=str(url))
    new_url.secret = uuid.uuid4()

    async def generate_short_code(secret: uuid.UUID):
      base = 0xFFFFFFFF & secret.int
      while True:
        short_code = base62.encode(base)
        async with session.begin():
          s = sa.select(Url).where(Url.secret == secret)
          response = await session.execute(sa.exists(s).select())
          exists = response.scalar()
        if exists == False:
          return short_code
        base ^= base

    new_url.short_code = await generate_short_code(new_url.secret)
    return new_url
