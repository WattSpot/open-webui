import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from open_webui.models.config import Config
from open_webui.models.chat_views import PanelTab


class FileConfigTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine('sqlite+aiosqlite://')
        async with self.engine.begin() as connection:
            await connection.run_sync(Config.__table__.create)
        sessions = async_sessionmaker(self.engine, expire_on_commit=False)

        @asynccontextmanager
        async def database():
            async with sessions() as session:
                yield session

        self.patch = patch('open_webui.models.config.get_async_db', database)
        self.patch.start()
        Config.configure(defaults={'ui.name': 'default', 'ui.other': 'default'})
        await Config.upsert({'ui.name': 'old database value', 'ui.other': 'user setting'})

    async def asyncTearDown(self):
        self.patch.stop()
        Config.configure()
        await self.engine.dispose()

    def test_preview_view_round_trip(self):
        tab = PanelTab(id='preview', kind='site-preview', label='Website', terminalId='owner', path='website')
        self.assertEqual(PanelTab.model_validate(tab.model_dump()).path, 'website')

    async def test_file_wins_on_every_read_and_survives_reconfigure(self):
        for _ in range(2):
            Config.configure(defaults={'ui.name': 'default'}, file_values={'ui.name': 'file'})
            self.assertEqual(await Config.get('ui.name'), 'file')
            self.assertEqual((await Config.get_many('ui.name', 'ui.other'))['ui.name'], 'file')
            self.assertEqual((await Config.get_namespace('ui'))['ui.name'], 'file')
            self.assertEqual((await Config.get_all())['ui.name'], 'file')
            self.assertEqual(await Config.get('ui.other'), 'user setting')
        await Config.upsert({'ui.name': 'file'})
        with self.assertRaises(ValueError):
            await Config.upsert({'ui.other': 'must not commit', 'ui.name': 'override'})
        self.assertEqual(await Config.get('ui.other'), 'user setting')
        with self.assertRaises(ValueError):
            await Config.delete('ui.name')
        Config.configure(defaults={'ui.name': 'default'})
        self.assertEqual(await Config.get('ui.name'), 'old database value')


if __name__ == '__main__':
    unittest.main()
