import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tickets import is_staff, ticket_overwrites, OpenTicket, CloseTicket, require_staff


class Entity:
    def __init__(self, identity):
        self.id = identity


class TicketTests(unittest.IsolatedAsyncioTestCase):
    async def test_buttons_survive_restart(self):
        self.assertTrue(OpenTicket().is_persistent())
        self.assertTrue(CloseTicket().is_persistent())

    async def test_only_named_roles_authorized(self):
        for identity in (1571479712453369916, 1571479796939231283):
            self.assertTrue(is_staff(SimpleNamespace(roles=[Entity(identity)])))
        self.assertFalse(is_staff(SimpleNamespace(roles=[Entity(123)], guild_permissions=SimpleNamespace(administrator=True))))

    async def test_creator_cannot_close(self):
        interaction = SimpleNamespace(user=Entity(42), guild=SimpleNamespace(
            fetch_member=AsyncMock(return_value=SimpleNamespace(roles=[]))),
            response=SimpleNamespace(send_message=AsyncMock()))
        with patch('tickets.db') as database:
            self.assertFalse(await require_staff(interaction))
            database.assert_not_called()
        interaction.response.send_message.assert_awaited_once()

    async def test_private_from_creation(self):
        roles = {i: Entity(i) for i in (1571479712453369916, 1571479796939231283)}
        guild = SimpleNamespace(default_role=Entity(1), me=Entity(2), get_role=roles.get)
        creator = Entity(3)
        overwrites = ticket_overwrites(guild, creator)
        self.assertEqual(len(overwrites), 5)
        self.assertFalse(overwrites[guild.default_role].view_channel)
        self.assertTrue(overwrites[creator].view_channel)
        self.assertFalse(overwrites[creator].manage_channels)
        self.assertFalse(overwrites[creator].manage_roles)
        for role in roles.values():
            self.assertTrue(overwrites[role].view_channel)

    async def test_missing_staff_role_fails_closed(self):
        guild = SimpleNamespace(get_role=lambda identity: None)
        with self.assertRaises(RuntimeError):
            ticket_overwrites(guild, Entity(3))
