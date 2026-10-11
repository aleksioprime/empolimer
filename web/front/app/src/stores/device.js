import { defineStore } from "pinia";
import resources from "@/services/resources";
import { LiveConnection } from "@/services/live";

let live = null;

export const useDeviceStore = defineStore("device", {
  state: () => ({
    devices: [],
    loaded: false,
    connection: 'connecting', // connecting | live | polling | offline
    lastUpdate: null,         // когда список последний раз пришёл с сервера
    error: null,
  }),
  getters: {
    byId: (state) => (id) => state.devices.find((device) => device.id === id),
    summary: (state) => ({
      total: state.devices.length,
      online: state.devices.filter((d) => d.online).length,
      warning: state.devices.filter((d) => d.state === 'warning').length,
      offline: state.devices.filter((d) => d.state === 'offline').length,
      waiting: state.devices.filter((d) => d.state === 'new').length,
    }),
  },
  actions: {
    _setDevices(devices) {
      this.devices = devices;
      this.loaded = true;
      this.lastUpdate = new Date();
      this.error = null;
    },
    // Загрузка списка устройств запросом; true — успешно
    async loadDevices() {
      const res = await resources.device.getDevices();
      if (res.__state === "success") {
        this._setDevices(res.data);
        return true;
      }
      this.error = res.data?.message || 'Не удалось загрузить устройства';
      return false;
    },
    // Живое обновление: WebSocket, при сбое — опрос запросами
    startLive() {
      if (!live) {
        live = new LiveConnection({
          onDevices: (devices) => this._setDevices(devices),
          onStatus: (status) => { this.connection = status; },
          poll: () => this.loadDevices(),
        });
      }
      live.start();
    },
    stopLive() {
      live?.stop();
    },
    async loadDevice(id) {
      const res = await resources.device.getDevice(id);
      if (res.__state === "success") {
        const index = this.devices.findIndex((d) => d.id === id);
        if (index >= 0) this.devices.splice(index, 1, res.data);
        else this.devices.push(res.data);
        return res.data;
      }
      return null;
    },
    async createDevice(data) {
      const res = await resources.device.createDevice(data);
      if (res.__state === "success") await this.loadDevices();
      return res;
    },
    async updateDevice(id, data) {
      const res = await resources.device.partialUpdateDevice(id, data);
      if (res.__state === "success") await this.loadDevices();
      return res;
    },
    async deleteDevice(id) {
      const res = await resources.device.deleteDevice(id);
      if (res.__state === "success") this.devices = this.devices.filter((d) => d.id !== id);
      return res.__state === "success";
    },
    async loadSeries(id, params) {
      const res = await resources.device.getDeviceSeries(id, { params });
      return res.__state === "success" ? res.data : null;
    },
    async loadData(id, params) {
      const res = await resources.device.getDeviceData(id, { params });
      return res.__state === "success" ? res.data : null;
    },
    async downloadData(id, params) {
      const res = await resources.device.downloadDeviceData(id, { params });
      return res.__state === "success" ? res.data : null;
    },
    async clearData(id) {
      const res = await resources.device.deleteDeviceData(id);
      return res.__state === "success";
    },
  }
});
