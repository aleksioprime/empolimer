import { UserResource } from "./user.resource";
import { AuthResource } from "./auth.resource";
import { DeviceResource } from "./device.resource";

export default {
    user: new UserResource(),
    auth: new AuthResource(),
    device: new DeviceResource(),
};