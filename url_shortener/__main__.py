import uuid
import dataclasses
import json

from aiohttp import web
import sqlalchemy as sa
import aiohttp_sqlalchemy as ahsa
from url_shortener.database import Url, init_db


async def url_create(request):
	try:
		json_request = await request.json()
	except Exception:
		raise web.HTTPBadRequest()
	if "url" not in json_request:
		raise web.HTTPBadRequest()
	sa_session = ahsa.get_session(request)
	try:
		url = await Url.create(url=json_request["url"], session=sa_session)
	except ValueError:
		raise web.HTTPBadRequest()
	sa_session.add(url)
	await sa_session.commit()
	return web.json_response(url.dict())


async def url_get(request):
	short_code = request.match_info["short_code"]
	
	sa_session = ahsa.get_session(request)
	response = await sa_session.execute(sa.select(Url).where(Url.short_code == short_code))
	url = response.scalar()
	if url is None:
		raise web.HTTPNotFound()
	raise web.HTTPMovedPermanently(url.url)


async def url_delete(request):
	if "secret" not in request.query:
		raise web.HTTPBadRequest()

	sa_session = ahsa.get_session(request)
	response = await sa_session.execute(sa.select(Url).where(Url.secret == uuid.UUID(request.query["secret"])))
	url = response.scalar()
	if url is not None:
		await sa_session.delete(url)
		await sa_session.commit()
	return web.Response()


async def app_factory():
	app = web.Application()
	await init_db(app)

	app.add_routes([web.post("/make_shorter", url_create)])
	app.add_routes([web.get("/{short_code}", url_get)])
	app.add_routes([web.delete("/delete", url_delete)])

	return app


if __name__ == "__main__":
	web.run_app(app_factory())
