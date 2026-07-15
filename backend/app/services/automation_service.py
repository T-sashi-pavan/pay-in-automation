import os
import time
import base64
import logging
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

def run_playwright_simulation(frontend_url: str, non_slab_rule: dict, slab_rule: dict = None) -> dict:
    """
    Launches Playwright headlessly, opens {frontend_url}/mock-crm,
    fills the forms for non-slab (and optionally slab), takes screenshots,
    and returns progress steps and base64 screenshots.
    """
    logger.info(f"[PLAYWRIGHT] Starting simulation targeting {frontend_url}")
    screenshots = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()
        
        try:
            # STEP 1: Fill Non-Slab Rule
            target_url = f"{frontend_url.rstrip('/')}/mock-crm"
            logger.info(f"[PLAYWRIGHT] Navigating to {target_url}")
            page.goto(target_url)
            page.wait_for_selector("#crm-entry-form")
            
            # Select Slab Type: Non-Slab
            page.select_option("#slab_type", "NON_SLAB")
            time.sleep(0.3)
            
            # Fill common fields
            fields_to_fill = {
                "#lob": non_slab_rule.get("lob") or "Motor",
                "#file_type": non_slab_rule.get("file_type") or "New",
                "#insurance_company": non_slab_rule.get("insurance_company") or "Unknown Insurer",
                "#product": non_slab_rule.get("product") or "Private Car",
                "#policy_type": non_slab_rule.get("policy_type") or "Comprehensive",
                "#plan_type": non_slab_rule.get("plan_type") or "1 Yr OD + 1 Yr TP",
                "#sub_product": non_slab_rule.get("sub_product") or "NA",
                "#class_": non_slab_rule.get("class") or "NA",
                "#sub_class": non_slab_rule.get("sub_class") or "NA",
                "#make": non_slab_rule.get("make") or "ANY",
                "#model": non_slab_rule.get("model") or "ANY",
                "#fuel_type": non_slab_rule.get("fuel_type") or "Petrol",
                "#cpa_status": non_slab_rule.get("cpa_status") or "Select CPA",
                "#ncb_status": non_slab_rule.get("ncb_status") or "Select NCB",
                "#vehicle_age_from": str(non_slab_rule.get("vehicle_age_from") or "0"),
                "#vehicle_age_to": str(non_slab_rule.get("vehicle_age_to") or "99"),
                "#source": non_slab_rule.get("source") or "Select Source",
                "#zone": non_slab_rule.get("zone") or "Select Zone",
                "#rto": non_slab_rule.get("rto") or "Select RTO",
                "#payin_remark": non_slab_rule.get("remarks") or "",
                "#effective_date": non_slab_rule.get("effective_date") or "",
                "#extra_remark": "Simulated Non-Slab Automation Entry",
                "#premium_type": "OD",  # Default premium type
                "#payin_od": str(non_slab_rule.get("payin_od") or "0"),
                "#payin_tp": str(non_slab_rule.get("payin_tp") or "0"),
                "#payin_net": str(non_slab_rule.get("payin_net") or "0"),
                "#payout_od": str(non_slab_rule.get("payout_od") or "0"),
                "#payout_tp": str(non_slab_rule.get("payout_tp") or "0"),
                "#payout_net": str(non_slab_rule.get("payout_net") or "0"),
                "#payin_reward": str(non_slab_rule.get("payin_reward") or "0"),
                "#payin_scheme": str(non_slab_rule.get("payin_scheme") or "0"),
            }
            
            for selector, val in fields_to_fill.items():
                if not val:
                    continue
                try:
                    el = page.locator(selector)
                    if el.count() > 0:
                        tag_name = page.eval_on_selector(selector, "el => el.tagName")
                        if tag_name == "SELECT":
                            page.select_option(selector, value=val)
                        else:
                            page.fill(selector, val)
                except Exception as e:
                    logger.warning(f"[PLAYWRIGHT] Field fill failed for {selector}: {e}")
            
            time.sleep(0.5)
            # Take screenshot before submitting non-slab
            scr_ns_filled = page.screenshot(full_page=False)
            screenshots["non_slab_filled"] = base64.b64encode(scr_ns_filled).decode("utf-8")
            
            # Submit form
            page.click("#submit_crm_form")
            time.sleep(0.5)
            
            # Take screenshot after submitting non-slab
            scr_ns_success = page.screenshot(full_page=False)
            screenshots["non_slab_submitted"] = base64.b64encode(scr_ns_success).decode("utf-8")
            
            # STEP 2: Fill Slab Rule if exists
            if slab_rule:
                logger.info("[PLAYWRIGHT] Navigating for Slab rule automation")
                # Navigate/reset page
                page.goto(target_url)
                page.wait_for_selector("#crm-entry-form")
                
                # Select Slab Type: Slab
                page.select_option("#slab_type", "SLAB")
                time.sleep(0.3)
                
                # Fill common fields from slab rule
                fields_to_fill_slab = {
                    "#lob": slab_rule.get("lob") or "Motor",
                    "#file_type": slab_rule.get("file_type") or "New",
                    "#insurance_company": slab_rule.get("insurance_company") or "Unknown Insurer",
                    "#product": slab_rule.get("product") or "Private Car",
                    "#policy_type": slab_rule.get("policy_type") or "Comprehensive",
                    "#plan_type": slab_rule.get("plan_type") or "1 Yr OD + 1 Yr TP",
                    "#sub_product": slab_rule.get("sub_product") or "NA",
                    "#class_": slab_rule.get("class") or "NA",
                    "#sub_class": slab_rule.get("sub_class") or "NA",
                    "#make": slab_rule.get("make") or "ANY",
                    "#model": slab_rule.get("model") or "ANY",
                    "#fuel_type": slab_rule.get("fuel_type") or "Petrol",
                    "#cpa_status": slab_rule.get("cpa_status") or "Select CPA",
                    "#ncb_status": slab_rule.get("ncb_status") or "Select NCB",
                    "#vehicle_age_from": str(slab_rule.get("vehicle_age_from") or "0"),
                    "#vehicle_age_to": str(slab_rule.get("vehicle_age_to") or "99"),
                    "#source": slab_rule.get("source") or "Select Source",
                    "#zone": slab_rule.get("zone") or "Select Zone",
                    "#rto": slab_rule.get("rto") or "Select RTO",
                    "#payin_remark": slab_rule.get("remarks") or "",
                    "#effective_date": slab_rule.get("effective_date") or "",
                    "#extra_remark": "Simulated Slab Automation Entry",
                }
                
                for selector, val in fields_to_fill_slab.items():
                    if not val:
                        continue
                    try:
                        el = page.locator(selector)
                        if el.count() > 0:
                            tag_name = page.eval_on_selector(selector, "el => el.tagName")
                            if tag_name == "SELECT":
                                page.select_option(selector, value=val)
                            else:
                                page.fill(selector, val)
                    except Exception as e:
                        logger.warning(f"[PLAYWRIGHT] Slab field fill failed for {selector}: {e}")
                
                # Fill Slab Details (simulated list of tiers)
                slabs = slab_rule.get("slabs") or []
                for idx, slab in enumerate(slabs):
                    try:
                        page.fill(f"#slab_from_{idx}", str(slab.get("slab_from") or "0"))
                        page.fill(f"#slab_to_{idx}", str(slab.get("slab_to") or "MAX"))
                        page.fill(f"#slab_payin_od_{idx}", str(slab.get("payin_od") or "0"))
                        page.fill(f"#slab_payin_tp_{idx}", str(slab.get("payin_tp") or "0"))
                        page.fill(f"#slab_payin_net_{idx}", str(slab.get("payin_net") or "0"))
                    except Exception as e:
                        logger.warning(f"[PLAYWRIGHT] Flipped/missing slab inputs for index {idx}: {e}")
                
                time.sleep(0.5)
                scr_s_filled = page.screenshot(full_page=False)
                screenshots["slab_filled"] = base64.b64encode(scr_s_filled).decode("utf-8")
                
                # Submit form
                page.click("#submit_crm_form")
                time.sleep(0.5)
                
                scr_s_success = page.screenshot(full_page=False)
                screenshots["slab_submitted"] = base64.b64encode(scr_s_success).decode("utf-8")
                
            browser.close()
            return {
                "success": True,
                "screenshots": screenshots,
                "error": None
            }
            
        except Exception as ex:
            logger.error(f"[PLAYWRIGHT] Exception during run: {ex}", exc_info=True)
            try:
                browser.close()
            except:
                pass
            return {
                "success": False,
                "screenshots": screenshots,
                "error": str(ex)
            }
