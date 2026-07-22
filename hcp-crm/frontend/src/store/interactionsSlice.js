import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import { createInteraction, updateInteraction } from "../api/client";

const initialFormState = {
  hcpName: "",
  interactionType: "Meeting",
  date: new Date().toISOString().slice(0, 10),
  time: new Date().toTimeString().slice(0, 5),
  attendees: "",
  topicsDiscussed: "",
  materialsShared: [],
  samplesDistributed: [],
  sentiment: "neutral",
  outcomes: "",
  followUpActions: "",
};

export const submitInteraction = createAsyncThunk(
  "interactions/submit",
  async (_, { getState }) => {
    const f = getState().interactions.form;
    const payload = {
      hcp_name: f.hcpName,
      interaction_type: f.interactionType,
      date: f.date,
      time: f.time,
      attendees: f.attendees,
      topics_discussed: f.topicsDiscussed,
      materials_shared: f.materialsShared,
      samples_distributed: f.samplesDistributed,
      sentiment: f.sentiment,
      outcomes: f.outcomes,
      follow_up_actions: f.followUpActions,
    };
    return await createInteraction(payload);
  }
);

export const patchInteraction = createAsyncThunk(
  "interactions/patch",
  async ({ id, updates }) => {
    return await updateInteraction(id, updates);
  }
);

const interactionsSlice = createSlice({
  name: "interactions",
  initialState: {
    form: initialFormState,
    lastSaved: null,
    status: "idle", // idle | saving | saved | error
    error: null,
  },
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    addMaterial(state, action) {
      if (!state.form.materialsShared.includes(action.payload)) {
        state.form.materialsShared.push(action.payload);
      }
    },
    removeMaterial(state, action) {
      state.form.materialsShared = state.form.materialsShared.filter(
        (m) => m !== action.payload
      );
    },
    addSample(state, action) {
      if (!state.form.samplesDistributed.includes(action.payload)) {
        state.form.samplesDistributed.push(action.payload);
      }
    },
    removeSample(state, action) {
      state.form.samplesDistributed = state.form.samplesDistributed.filter(
        (s) => s !== action.payload
      );
    },
    resetForm(state) {
      state.form = { ...initialFormState, date: new Date().toISOString().slice(0, 10) };
    },
    hydrateFromAgent(state, action) {
      // Merge fields coming back from the AI chat assistant into the form
      const interaction = action.payload;
      if (!interaction) return;
      state.form.hcpName = interaction.hcp_name || state.form.hcpName;
      state.form.topicsDiscussed = interaction.topics_discussed || state.form.topicsDiscussed;
      state.form.attendees = interaction.attendees || state.form.attendees;
      state.form.sentiment = interaction.sentiment || state.form.sentiment;
      state.form.outcomes = interaction.outcomes || state.form.outcomes;
      state.form.followUpActions = interaction.follow_up_actions || state.form.followUpActions;
      state.form.materialsShared = interaction.materials_shared?.length
        ? interaction.materials_shared
        : state.form.materialsShared;
      state.form.samplesDistributed = interaction.samples_distributed?.length
        ? interaction.samples_distributed
        : state.form.samplesDistributed;
      state.lastSaved = interaction;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.status = "saving";
        state.error = null;
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.status = "saved";
        state.lastSaved = action.payload;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.status = "error";
        state.error = action.error.message;
      })
      .addCase(patchInteraction.fulfilled, (state, action) => {
        state.lastSaved = action.payload;
      });
  },
});

export const {
  updateField,
  addMaterial,
  removeMaterial,
  addSample,
  removeSample,
  resetForm,
  hydrateFromAgent,
} = interactionsSlice.actions;
export default interactionsSlice.reducer;