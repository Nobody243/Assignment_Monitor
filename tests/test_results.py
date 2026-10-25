import results
import tracker

# A trimmed copy of the CMS Provisional Result page layout (synthetic data): one table per semester with a
# caption, the student table without one, the GPA/CGPA footer row, N/A for the running semester.
RESULTS = """
<table class="table tableCol4">
 <tr><td>Enrollment</td><td>01-000000-000</td><td>Registration No.</td><td>1</td></tr>
 <tr><td>Name</td><td>A STUDENT</td><td>Father Name</td><td>A PARENT</td></tr>
 <tr><td>Program</td><td>BS (IT)</td><td>Intake Semester</td><td>Fall-2023</td></tr>
</table>
<table class="table"><caption>Fall-2023</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>CSC 101</td><td>Programming</td><td>N/A</td><td>3</td><td>A</td><td>4</td><td>12</td></tr>
 <tr><td>2</td><td>CSL 101</td><td>Programming Lab</td><td>N/A</td><td>1</td><td>B+</td><td>3.33</td><td>3.33</td></tr>
 <tr><td>3</td><td>ISL 100</td><td>Tajweed</td><td>N/A</td><td>0</td><td>B</td><td>3</td><td>0</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> 3.83,
   <strong>CGPA:</strong> 3.83</td></tr>
</table>
<table class="table"><caption>Spring-2024</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>GSC 200</td><td>Calculus</td><td>N/A</td><td>3</td><td>C</td><td>2</td><td>6</td></tr>
 <tr><td>2</td><td>ENG 100</td><td>English</td><td>N/A</td><td>3</td><td>F</td><td>0</td><td>0</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> 1,
   <strong>CGPA:</strong> 2.13</td></tr>
</table>
<table class="table"><caption>Fall-2024</caption>
 <tr><th>#</th><th>Code</th><th>Title</th><th>Majors</th><th>Credit Hours</th><th>Grade</th><th>Grade Points</th><th>Product</th></tr>
 <tr><td>1</td><td>ENG 100</td><td>English</td><td>N/A</td><td>3</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>
 <tr><td>2</td><td>SEN 300</td><td>Software Engineering</td><td>N/A</td><td>2</td><td>N/A</td><td>N/A</td><td>N/A</td></tr>
 <tr><td colspan="8" class="text-right"><strong>GPA:</strong> N/A,
   <strong>CGPA:</strong> N/A</td></tr>
</table>
"""


def test_parse_results_reads_student_semesters_and_footers():
    d = results.parse_results(RESULTS)
    assert d["student"]["program"] == "BS (IT)" and d["student"]["intake_semester"] == "Fall-2023"
    names = [s["name"] for s in d["semesters"]]
    assert names == ["Fall-2023", "Spring-2024", "Fall-2024"]
    first = d["semesters"][0]
    assert first["gpa"] == 3.83 and first["cgpa"] == 3.83 and first["complete"]
    assert first["courses"][1] == {"code": "CSL 101", "title": "Programming Lab", "credits": 1.0, "grade": "B+",
                                   "points": 3.33, "product": 3.33}
    running = d["semesters"][2]
    assert running["gpa"] is None and running["cgpa"] is None and not running["complete"]
    assert running["courses"][0]["grade"] == "" and running["courses"][0]["points"] is None


def test_gpa_arithmetic_matches_the_portal():
    d = results.parse_results(RESULTS)
    s1, s2 = d["semesters"][0], d["semesters"][1]
    assert results.gpa_of(s1["courses"]) == 3.83          # (12 + 3.33) / 4; the zero-credit course weighs nothing
    assert results.gpa_of(s2["courses"]) == 1.0
    t = results.totals([s1, s2])
    assert t["credits"] == 10 and t["earned"] == 7 and t["cgpa"] == 2.13
    assert results.gpa_of(d["semesters"][2]["courses"]) is None


def test_what_if_projection_and_required_gpa():
    d = results.parse_results(RESULTS)
    sems = d["semesters"]
    assert results.current_semester(sems)["name"] == "Fall-2024"
    p = results.project(sems, {"ENG 100": "A"})
    assert p["gpa"] == 4.0 and p["picked"] == 1 and p["of"] == 2
    assert p["cgpa"] == round((21.33 + 12) / 13, 2)
    p2 = results.project(sems, {"ENG 100": "A", "SEN 300": "B"})
    assert p2["gpa"] == round((12 + 6) / 5, 2) and p2["cgpa"] == round((21.33 + 18) / 15, 2)
    need = results.required_gpa(sems, 2.5)
    assert need == round((2.5 * 15 - 21.33) / 5, 2)
    assert results.project([s for s in sems if s["complete"]], {})["gpa"] is None


def test_newly_graded_is_quiet_on_first_read_and_reports_new_grades():
    d = results.parse_results(RESULTS)
    assert results.newly_graded(None, d) == []
    assert results.newly_graded(d, d) == []
    later = results.parse_results(RESULTS.replace("<td>3</td><td>N/A</td><td>N/A</td><td>N/A</td>",
                                                  "<td>3</td><td>A-</td><td>3.67</td><td>11.01</td>"))
    posted = results.newly_graded(d, later)
    assert [s["name"] for s in posted] == ["Fall-2024"]
    assert results.graded_count(posted[0]) == 1 and not posted[0]["complete"]


def test_tracker_stores_results_and_returns_posted(tmp_path, monkeypatch):
    monkeypatch.setattr(tracker, "RESULTS_PATH", tmp_path / "results.json")
    d = results.parse_results(RESULTS)
    assert tracker.save_results(d) == []                   # first read: stored, nothing announced
    assert tracker.load_results()["semesters"][0]["name"] == "Fall-2023"
    later = results.parse_results(RESULTS.replace("<td>2</td><td>N/A</td><td>N/A</td><td>N/A</td>",
                                                  "<td>2</td><td>B</td><td>3</td><td>6</td>"))
    posted = tracker.save_results(later)
    assert [s["name"] for s in posted] == ["Fall-2024"]
    assert tracker.save_results({"student": {}, "semesters": []}) == []   # an empty read never overwrites
    assert len(tracker.load_results()["semesters"]) == 3


def test_overrides_scenarios_and_grade_needed():
    d = results.parse_results(RESULTS)
    sems = d["semesters"]
    # a past grade changed hypothetically: that semester's GPA and the cumulative figure follow, nothing else moves
    alt = results.apply_overrides(sems, {("Spring-2024", "ENG 100"): "A"})
    assert results.gpa_of(alt[1]["courses"]) == 3.0 and results.gpa_of(sems[1]["courses"]) == 1.0
    assert results.totals(alt[:2])["cgpa"] == round((15.33 + 6 + 12) / 10, 2)
    assert alt[2]["courses"][0]["grade"] == ""              # the running semester is not touched
    assert results.apply_overrides(sems, {("Fall-2024", "ENG 100"): "A"})[2]["courses"][0]["grade"] == ""
    # uniform scenarios: straight A's and straight F's in the running semester
    scen = {x["grade"]: x for x in results.uniform_scenarios(sems)}
    assert scen["A"]["gpa"] == 4.0 and scen["A"]["cgpa"] == round((21.33 + 20) / 15, 2)
    assert scen["F"]["gpa"] == 0.0 and scen["F"]["cgpa"] == round(21.33 / 15, 2)
    # with one course picked, the scenario fills only the other one
    scen2 = {x["grade"]: x for x in results.uniform_scenarios(sems, {"ENG 100": "C"})}
    assert scen2["A"]["gpa"] == round((6 + 8) / 5, 2)
    # the lowest grade that still reaches a target, and an unreachable one
    need = results.grade_needed(sems, {}, 2.5)
    assert need["reached"] and need["grade"] == "B+" and need["remaining"] == 2 and need["best"] == scen["A"]["cgpa"]
    assert results.grade_needed(sems, {}, 3.9) == {"grade": None, "best": scen["A"]["cgpa"], "remaining": 2, "reached": False}
    full = results.grade_needed(sems, {"ENG 100": "A", "SEN 300": "A"}, 2.5)
    assert full["remaining"] == 0 and full["reached"]
    assert results.uniform_scenarios(sems[:2]) == []
