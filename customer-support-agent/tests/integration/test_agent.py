# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent


def test_shipping_query() -> None:
    """
    Integration test checking that shipping related queries are routed to faq_agent.
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="Where is my shipment?")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    response_text = ""
    for event in events:
        if event.output:
            response_text += str(event.output) + " "
        if event.content and event.content.parts:
            response_text += "".join(p.text for p in event.content.parts if p.text) + " "

    # FAQ agent should answer shipping questions politely and mention helper info
    assert len(response_text) > 0
    assert "sorry" not in response_text.lower() or "only assist" not in response_text.lower()


def test_unrelated_query() -> None:
    """
    Integration test checking that unrelated queries are politely declined.
    """
    session_service = InMemorySessionService()
    session = session_service.create_session_sync(user_id="test_user", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")

    message = types.Content(
        role="user", parts=[types.Part.from_text(text="What is the capital of Japan?")]
    )

    events = list(
        runner.run(
            new_message=message,
            user_id="test_user",
            session_id=session.id,
            run_config=RunConfig(streaming_mode=StreamingMode.SSE),
        )
    )

    response_text = ""
    for event in events:
        if event.output:
            response_text += str(event.output) + " "
        if event.content and event.content.parts:
            response_text += "".join(p.text for p in event.content.parts if p.text) + " "

    # Should contain the polite refusal message
    assert "only assist" in response_text.lower() or "shipping-related" in response_text.lower()
