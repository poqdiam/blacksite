import sqlite3, json, os

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "blacksite.db")

def seed():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Fix swiftcsp 2.11A
    cur.execute("SELECT cf.id FROM compliance_frameworks cf WHERE cf.short_name='swiftcsp'")
    r = cur.fetchone()
    if r:
        cur.execute("""UPDATE catalog_controls SET description=?, parameters_json=?
            WHERE framework_id=? AND control_id='2.11A'""",
            ("Relationship Management Application (RMA) Restriction: SWIFT messaging through the RMA is restricted to authorized correspondents. Unused RMA relationships are terminated to reduce the attack surface for fraudulent message routing.",
             json.dumps({"examine":["RMA authorization records","Active RMA correspondent list","RMA review and cleanup records"],"interview":["SWIFT administrator","Compliance / correspondent banking team","CISO"],"test":["Verify RMA list is reviewed and unauthorized correspondents removed","Confirm RMA addition requires formal authorization","Review RMA change records for unauthorized modifications"]}),
             r[0]))
        print(f"swiftcsp 2.11A: {cur.rowcount} updated")

    # Generic template for frameworks where title is self-explanatory
    generic_fws = ["csaccm","naic","nerccip","nydfs500","tsapipeline","basel3"]
    for fw_sn in generic_fws:
        cur.execute("SELECT cf.id FROM compliance_frameworks cf WHERE cf.short_name=?", (fw_sn,))
        r = cur.fetchone()
        if not r: continue
        fw_id = r[0]
        cur.execute("""SELECT id, control_id, title, domain FROM catalog_controls
            WHERE framework_id=? AND (description IS NULL OR description='')""", (fw_id,))
        rows = cur.fetchall()
        cnt = 0
        for row_id, ctrl_id, title, domain in rows:
            desc = f"{title}: This control requires organizations to implement and maintain policies, procedures, and technical measures to satisfy {fw_sn.upper()} requirements. Evidence of implementation, documentation, and operational effectiveness is required during compliance assessments."
            params = json.dumps({
                "examine":[f"Policy and procedure documentation for {title.split(':')[0] if ':' in title else title}","Implementation evidence","Risk assessment","Annual review records"],
                "interview":["CISO / compliance officer","System owner","Internal / external auditor"],
                "test":[f"Verify control is implemented and documented","Review evidence of operational effectiveness","Confirm compliance with applicable requirements"]
            })
            cur.execute("UPDATE catalog_controls SET description=?, parameters_json=? WHERE id=?", (desc, params, row_id))
            cnt += cur.rowcount
        print(f"{fw_sn}: {cnt} updated")

    # Copy NIST 800-53 descriptions/params to baseline frameworks
    baselines = ["nist_low","nist_mod","nist_high","nist_all","nist_privacy"]
    for bfw in baselines:
        cur.execute("SELECT id FROM compliance_frameworks WHERE short_name=?", (bfw,))
        r = cur.fetchone()
        if not r: continue
        cur.execute("""UPDATE catalog_controls AS t
            SET description=(SELECT s.description FROM catalog_controls s
                JOIN compliance_frameworks f ON s.framework_id=f.id
                WHERE f.short_name='nist80053r5' AND s.control_id=t.control_id
                  AND s.description IS NOT NULL AND s.description!=''),
            parameters_json=(SELECT s.parameters_json FROM catalog_controls s
                JOIN compliance_frameworks f ON s.framework_id=f.id
                WHERE f.short_name='nist80053r5' AND s.control_id=t.control_id
                  AND s.parameters_json IS NOT NULL AND s.parameters_json!='')
            WHERE t.framework_id=? AND (t.description IS NULL OR t.description='')""", (r[0],))
        print(f"{bfw}: {cur.rowcount} copied from nist80053r5")

    conn.commit()
    conn.close()
    print("Done.")

seed()
