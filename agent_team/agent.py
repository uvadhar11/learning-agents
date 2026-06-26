# @title Define the get_weather Tool
from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from websockets import asyncio
from google.genai import types # used for creating message Content and Parts (built in types)



def get_weather(city: str) -> dict:
    # docstring is important for each tool, it tells the agent: What the tool does, When to use it, What arguments it requires (city: str), and What information it returns.
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---") # print tool execution for debugging
    city_normalized = city.lower().replace(" ", "") # normalize city name for consistent lookup

    # Mock weather data, API later for real implementation
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have weather information for '{city}'."}

# @title Define the Weather Agent
# Use one of the model constants defined earlier
AGENT_MODEL = "gemini-2.5-flash" # Starting with Gemini

weather_agent = Agent(
    name="weather_agent_v1",
    model=AGENT_MODEL, # Can be a string for Gemini or a LiteLlm object
    description="Provides weather information for specific cities.",
    instruction="You are a helpful weather assistant. "
                "When the user asks for the weather in a specific city, "
                "use the 'get_weather' tool to find the information. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the weather report clearly.",
    tools=[get_weather], # Pass the function directly
)

print(f"Agent '{weather_agent.name}' created using model '{AGENT_MODEL}'.")



# Session Service and Runner
# -> SessionService stores conversation history & state.
# multiple types of memory, InMemorySessionService is simple, non-persistent storage
session_service = InMemorySessionService()

# Constants for identifying the interaction context
APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001" # fixed ID for simplicity

# Create the conversation session
async def init_session(app_name:str, user_id:str, session_id:str) -> InMemorySessionService:
    session = await session_service.create_session(
        app_name = app_name,
        user_id = user_id,
        session_id = session_id
    )
    # print(f"Session created: App='{app_name}', User='{user_id}', Session='{session_id}'")
    return session

# use asyncio.run to execute the async function and get the session object
session = asyncio.run(init_session(APP_NAME, USER_ID, SESSION_ID))

# Runner: used for orchestrating the agent execution loop, managing interactions, and maintaining state.
runner = Runner(
    agent = weather_agent, # the agent we want to run
    app_name = APP_NAME,   # associates runs with our app
    session_service = session_service # uses our defined session manager
)
# print(f"Runner created for agent '{runner.agent.name}'.")


# AGENT INTERACTION
# async method because agent tools and execution can take time
async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response.""" # remember the tool description so the agent knows how to use it
  print(f"\n>>> User Query: {query}")

  # need to convert the user query into a Content object with Parts for the agent to process
  # for Content, its a specific object format. role is user to tell this is a user prompt, and this is different from role=model
  # Parts are simply a small unit of a message, here we only have one part which is the text of the query
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response."

  # run_async executed agent logic and gives us a list of all events, so we iterate through them
  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      # here, we pass in the user id, session id, and new message content we created above. The runner will handle the agent's processing and return events as they occur.
      print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}") # prints all events

      # is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")


# Run the Initial Conversation
# We need an async function to await our interaction helper
async def run_conversation():
    await call_agent_async("What is the weather like in London?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)

    await call_agent_async("How about Paris?",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID) # Expecting the tool's error message

    await call_agent_async("Tell me the weather in New York",
                                       runner=runner,
                                       user_id=USER_ID,
                                       session_id=SESSION_ID)

# Execute the conversation (using terminal not adk web for testing)
if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")