// k6 ramp used for the scale-out measurement on both stacks.
//   k6 run -e URL=http://<alb-dns> bench/ramp.js
import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    ramp: {
      executor: "ramping-arrival-rate",
      startRate: 20,
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 400,
      stages: [
        { target: 20, duration: "1m" },   // baseline: one task/pod
        { target: 400, duration: "2m" },  // ramp to force scale-out 1 -> ~10
        { target: 400, duration: "4m" },  // hold while scaling completes
        { target: 20, duration: "2m" },   // scale-in
      ],
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

export default function () {
  const res = http.get(`${__ENV.URL}/`);
  check(res, { "200": (r) => r.status === 200 });
}
