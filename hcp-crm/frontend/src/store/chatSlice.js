import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { sendChatMessage } from "../api/client";

const sessionId =
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `session-${Date.now()}`;

export const sendMessage = createAsyncThunk(
  "chat/sendMessage",
  async (message) => {
    const data = await sendChatMessage(sessionId, message);
    return { message, data };
  }
);

const chatSlice = createSlice({
  name: "chat",
  initialState: {
    sessionId,
    messages: [
      {
        role: "assistant",
        content:
          'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      },
    ],
    status: "idle",
    lastInteraction: null,
    suggestedFollowups: [],
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = "loading";
        state.messages.push({ role: "user", content: action.meta.arg });
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.status = "idle";
        const { data } = action.payload;
        state.messages.push({ role: "assistant", content: data.reply });
        state.lastInteraction = data.interaction || state.lastInteraction;
        state.suggestedFollowups = data.suggested_followups?.length
          ? data.suggested_followups
          : state.suggestedFollowups;
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = "error";
        state.messages.push({
          role: "assistant",
          content: `Sorry, something went wrong: ${action.error.message}`,
        });
      });
  },
});

export default chatSlice.reducer;
