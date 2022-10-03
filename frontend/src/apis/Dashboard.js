import axios from "axios";
import cookies from "js-cookies";

axios.defaults.xsrfHeaderName = "X-CSRFToken";

export async function loadDash() {
  const api = await axios.get(`/ghosts/api/ghost/list`);
  console.log(`get structure list in api`);
  console.log(api);
  return api.data;
}

export async function postOpenChar(character_id) {
  console.log(`sent open request ${character_id}`);
  const api = await axios.post(
    `/ghosts/api/ghost/kick?character_id=${character_id}`,
    { character_id: character_id },
    { headers: { "X-CSRFToken": cookies.getItem("csrftoken") } },
  );
  return api.data;
}
