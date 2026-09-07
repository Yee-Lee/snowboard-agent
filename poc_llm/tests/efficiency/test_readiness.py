from __future__ import annotations

import unittest

from poc_llm.harness.mva_contract import SESSION_FACTS
from poc_llm.efficiency.readiness import ConversationReadinessPool, ReadinessError, ReadinessIdentity


IDENTITY = ReadinessIdentity("facts", "profile", 1)


class ConversationReadinessPoolTests(unittest.TestCase):
    def setUp(self):
        self.closed = []
        self.subject = ConversationReadinessPool(self.closed.append, hold_seconds=30)

    def test_clean_hold_adopt_and_release(self):
        conversation = object()
        ticket = self.subject.begin_open(IDENTITY, SESSION_FACTS)
        self.assertEqual(self.subject.live_count, 1)
        self.assertTrue(self.subject.finish_open(ticket, conversation, now=10))
        self.assertIs(self.subject.adopt(IDENTITY, now=40), conversation)
        self.assertEqual(self.subject.state, "ADOPTED")
        self.subject.release_adopted(conversation)
        self.assertEqual(self.closed, [conversation])
        self.assertEqual(self.subject.live_count, 0)

    def test_expired_or_mismatched_hold_is_closed_not_adopted(self):
        for identity, now in ((IDENTITY, 40.001), (ReadinessIdentity("other", "profile", 1), 20)):
            with self.subTest(identity=identity, now=now):
                closed = []
                subject = ConversationReadinessPool(closed.append, hold_seconds=30)
                conversation = object()
                ticket = subject.begin_open(IDENTITY, SESSION_FACTS)
                subject.finish_open(ticket, conversation, now=10)
                self.assertIsNone(subject.adopt(identity, now=now))
                self.assertEqual(closed, [conversation])
                self.assertEqual(subject.state, "EMPTY")

    def test_cancel_during_open_closes_late_native_return(self):
        conversation = object()
        ticket = self.subject.begin_open(IDENTITY, SESSION_FACTS)
        self.assertTrue(self.subject.cancel_open())
        self.assertFalse(self.subject.finish_open(ticket, conversation, now=10))
        self.assertEqual(self.closed, [conversation])
        self.assertEqual(self.subject.live_count, 0)

    def test_single_flight_and_no_request_hold_close(self):
        ticket = self.subject.begin_open(IDENTITY, SESSION_FACTS)
        with self.assertRaises(ReadinessError):
            self.subject.begin_open(IDENTITY, SESSION_FACTS)
        conversation = object()
        self.subject.finish_open(ticket, conversation, now=10)
        self.assertTrue(self.subject.close_unclaimed())
        self.assertFalse(self.subject.close_unclaimed())
        self.assertEqual(self.closed, [conversation])

    def test_adopted_identity_cannot_be_reused_for_new_session(self):
        first = object()
        ticket = self.subject.begin_open(IDENTITY, SESSION_FACTS)
        self.subject.finish_open(ticket, first, now=10)
        self.assertIs(self.subject.adopt(IDENTITY, now=11), first)
        self.assertIsNone(self.subject.adopt(IDENTITY, now=12))
        self.subject.release_adopted(first)
        second = object()
        ticket = self.subject.begin_open(IDENTITY, SESSION_FACTS)
        self.subject.finish_open(ticket, second, now=20)
        self.assertIs(self.subject.adopt(IDENTITY, now=21), second)
        self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
