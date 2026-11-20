import test from "node:test";
import assert from "node:assert/strict";
import { gpaOf, cgpaAfter, neededGpa, lowestGradeFor, creditsOf } from "../src/lib/gpa.js";

const sem = [
  { credits: "3", grade: "A" }, { credits: "3", grade: "B+" }, { credits: "2", grade: "B" }, { credits: "1", grade: "A-" },
];

test("the worked example in the CGPA guide: GPA 3.52", () => {
  assert.equal(gpaOf(sem), 3.52);
  assert.equal(creditsOf(sem), 9);
});

test("the CGPA carries earlier credits: 60 credits and 210 points gives 3.50", () => {
  assert.equal(cgpaAfter(sem, 3.5, 60), 3.5);
});

test("rows without a grade or without credits are ignored", () => {
  assert.equal(gpaOf([{ credits: "3", grade: "" }, { credits: "0", grade: "A" }, { credits: "x", grade: "A" }]), null);
  assert.equal(gpaOf([{ credits: "3", grade: "B" }, { credits: "3", grade: "" }]), 3);
});

test("zero-credit rows weigh nothing", () => {
  assert.equal(gpaOf([{ credits: "3", grade: "A" }, { credits: "0", grade: "F" }]), 4);
});

test("the target example: 3.60 over 84 credits needs a 4.05 semester, which is out of reach", () => {
  const r = neededGpa(3.6, 241.66 / 69, 69, 15);                 // 241.66 points over 69 credits, as in the guide
  assert.equal(r.needed, 4.05);
  assert.equal(r.reachable, false);
  assert.equal(lowestGradeFor(r.needed), null);
});

test("a reachable target names the lowest grade that gets there", () => {
  const r = neededGpa(3.4, 3.5, 69, 15);
  assert.equal(r.reachable, true);
  assert.equal(r.needed, 2.94);
  assert.equal(lowestGradeFor(r.needed), "B");                    // B is 3.00, the lowest letter at or above 2.94
});

test("grade lookup is monotonic", () => {
  assert.equal(lowestGradeFor(4), "A");
  assert.equal(lowestGradeFor(3.0), "B");
  assert.equal(lowestGradeFor(0), "F");
});

test("no earlier credits: the CGPA is the semester GPA, and the target is the GPA itself", () => {
  assert.equal(cgpaAfter(sem, "", ""), 3.52);
  assert.equal(neededGpa(3.0, "", "", 9).needed, 3.0);
});
