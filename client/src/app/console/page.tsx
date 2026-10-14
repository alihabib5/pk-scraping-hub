import { redirect } from "next/navigation";

/** `/console` has no meaning on its own — send it to the first source. */
export default function ConsoleIndex() {
  redirect("/console/ppra");
}
