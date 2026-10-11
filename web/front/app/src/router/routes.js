import { isLoggedIn } from "@/middlewares/isLoggedIn";

export const routes = [
  {
    path: "/",
    component: () => import("@/layouts/AppLayout.vue"),
    meta: {
      middlewares: [isLoggedIn],
    },
    children: [
      {
        path: "",
        name: "devices",
        component: () => import("@/views/DevicesOverview.vue"),
        meta: { title: 'Устройства' },
      },
      {
        path: "devices/:id",
        name: "device",
        component: () => import("@/views/DeviceDetail.vue"),
        meta: { title: 'Устройство' },
      },
      {
        path: "profile",
        name: "profile",
        component: () => import("@/views/Profile.vue"),
        meta: { title: 'Профиль' },
      },
      {
        path: "users",
        name: "users",
        component: () => import("@/views/Users.vue"),
        meta: { title: 'Пользователи' },
      },
    ]
  },
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/Login.vue"),
    meta: { title: 'Вход' },
  },
  { path: "/:pathMatch(.*)*", redirect: { name: "devices" } },
]
