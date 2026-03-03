import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../api/client';

export const fetchChannels = createAsyncThunk('channels/fetchAll', async () => {
  const res = await api.get('/channels/');
  return res.data;
});

export const createChannel = createAsyncThunk('channels/create', async (data) => {
  const res = await api.post('/channels/', data);
  return res.data;
});

export const startChannel = createAsyncThunk('channels/start', async (id) => {
  const res = await api.post(`/channels/${id}/start`);
  return res.data;
});

export const stopChannel = createAsyncThunk('channels/stop', async (id) => {
  const res = await api.post(`/channels/${id}/stop`);
  return res.data;
});

export const deleteChannel = createAsyncThunk('channels/delete', async (id) => {
  await api.delete(`/channels/${id}`);
  return id;
});

const channelsSlice = createSlice({
  name: 'channels',
  initialState: { items: [], status: 'idle', error: null },
  reducers: {
    upsertChannel(state, action) {
      const idx = state.items.findIndex((c) => c.id === action.payload.id);
      if (idx >= 0) state.items[idx] = { ...state.items[idx], ...action.payload };
      else state.items.unshift(action.payload);
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchChannels.pending, (s) => { s.status = 'loading'; })
      .addCase(fetchChannels.fulfilled, (s, a) => { s.status = 'idle'; s.items = a.payload; })
      .addCase(fetchChannels.rejected, (s, a) => { s.status = 'error'; s.error = a.error.message; })
      .addCase(createChannel.fulfilled, (s, a) => { s.items.unshift(a.payload); })
      .addCase(startChannel.fulfilled, (s, a) => {
        const idx = s.items.findIndex((c) => c.id === a.payload.id);
        if (idx >= 0) s.items[idx] = a.payload;
      })
      .addCase(stopChannel.fulfilled, (s, a) => {
        const idx = s.items.findIndex((c) => c.id === a.payload.id);
        if (idx >= 0) s.items[idx] = a.payload;
      })
      .addCase(deleteChannel.fulfilled, (s, a) => {
        s.items = s.items.filter((c) => c.id !== a.payload);
      });
  },
});

export const { upsertChannel } = channelsSlice.actions;
export default channelsSlice.reducer;
