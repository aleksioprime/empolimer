import { ApiService } from "@/services/api/api.service";

export class DeviceResource extends ApiService {
  constructor() {
    super();
  }

  getDevices(config) {
    return this.$get(`/api/v1/devices/`, config);
  }

  getDevice(id) {
    return this.$get(`/api/v1/devices/${id}/`);
  }

  createDevice(data) {
    return this.$post(`/api/v1/devices/`, data);
  }

  partialUpdateDevice(id, data) {
    return this.$patch(`/api/v1/devices/${id}/`, data);
  }

  deleteDevice(id) {
    return this.$delete(`/api/v1/devices/${id}/`);
  }

  getDeviceData(id, config) {
    return this.$get(`/api/v1/devices/${id}/data/`, config);
  }

  getDeviceSeries(id, config) {
    return this.$get(`/api/v1/devices/${id}/data/series/`, config);
  }

  downloadDeviceData(id, config = {}) {
    return this.$get(`/api/v1/devices/${id}/data/export/`, { ...config, responseType: 'blob' });
  }

  deleteDeviceData(id) {
    return this.$delete(`/api/v1/devices/${id}/data/`);
  }
}
