# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk import Workflow, Event
from google.adk.workflow import node
from google.adk.models import Gemini
from google.genai import types
from dotenv import load_dotenv

import os
import google.auth

# Load environment variables (like GEMINI_API_KEY) from .env file
load_dotenv()

# Vertex AI settings / Gemini fallback
try:
    _, project_id = google.auth.default()
    if project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    else:
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
except Exception:
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"


# 1. Define Classifier Agent to categorize user query
classifier_agent = Agent(
    name="classifier_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="Classify the user's query. If it is related to shipping (such as rates, tracking, delivery, returns, packaging, carrier), reply with 'shipping'. If it is unrelated to shipping, reply with 'unrelated'. Reply with exactly one word: 'shipping' or 'unrelated'."
)

# 2. Define Routing Node to inspect classifier's output and set route
@node
def route_node(ctx, node_input: str) -> Event:
    route_val = node_input.strip().lower()
    if "shipping" in route_val:
        return Event(output="shipping", actions={"route": "shipping"})
    return Event(output="unrelated", actions={"route": "unrelated"})

# 3. Define FAQ Agent to handle shipping-related support questions
faq_agent = Agent(
    name="faq_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="You are a shipping company support agent. Answer the user's shipping question (rates, tracking, delivery, returns) politely, clearly, and accurately based on the query they typed."
)

# 4. Define Decline Node to politely reject non-shipping queries
@node
def decline_node(ctx, node_input: str) -> str:
    return "I'm sorry, I can only assist with shipping-related queries (such as rates, tracking, delivery, or returns). Please let me know if you have a shipping question!"

# 5. Define Graph Workflow representing the orchestration structure
root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", classifier_agent),
        (classifier_agent, route_node),
        (route_node, {
            "shipping": faq_agent,
            "unrelated": decline_node
        })
    ]
)

# 6. Initialize App with the root Workflow agent
app = App(
    root_agent=root_agent,
    name="app",
)
