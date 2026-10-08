-- Copyright 2026 loke contributors
-- SPDX-License-Identifier: Apache-2.0
--
-- F3b.10: three requests' privacy_layer_metrics rows, in the shape core.audit.layermetrics.record
-- writes them, for scripts/smoke_ui.sh to load into the throwaway loke's database before
-- tests/ui/layermetrics_f3b10.json. Dated 2026-01-01 and 2026-01-02 (UTC), so the per-day
-- rows are known whatever day the smoke runs. The figures the dashboard must show:
--   requests 3
--   2026-01-01 ner   1 request, 1 detection, 1 accepted
--   2026-01-01 regex 1 request, 2 detections, 2 accepted
--   2026-01-02 ner   2 requests (one unavailable), 0 detections, 0 accepted
--   2026-01-02 regex 2 requests, 1 detection, 1 accepted
--   agreement over the 2 runs with two or more voters: 1 of 3 resolved, 33.3%
--   by type: ner PERSON 1/1, regex email 3/3
-- No value column exists, so none is written.
INSERT INTO privacy_layer_metrics (correlation_id,seq,kind,layer_id,entity_type,state,mode,duration_ms,detections,accepted,routed,conf_min_milli,conf_max_milli,conf_sum_milli,strategy,vetoed_by,voters,resolved,masked,passed,agreed,routing_notes,created_at) VALUES
 ('ui-f3b10-1',0,'layer','regex','','completed','detect-and-mask',0,2,2,2,950,950,1900,'','',0,0,0,0,0,'',1767225600000),
 ('ui-f3b10-1',1,'type','regex','email','completed','detect-and-mask',NULL,2,2,2,950,950,1900,'','',0,0,0,0,0,'',1767225600000),
 ('ui-f3b10-1',2,'layer','ner','','completed','detect-and-mask',40,1,1,1,800,800,800,'','',0,0,0,0,0,'',1767225600000),
 ('ui-f3b10-1',3,'type','ner','PERSON','completed','detect-and-mask',NULL,1,1,1,800,800,800,'','',0,0,0,0,0,'',1767225600000),
 ('ui-f3b10-1',4,'consensus','','','','',NULL,0,0,0,0,0,0,'most-restrictive','',2,2,2,0,1,'',1767225600000),
 ('ui-f3b10-2',0,'layer','regex','','completed','detect-and-mask',0,1,1,1,950,950,950,'','',0,0,0,0,0,'',1767312000000),
 ('ui-f3b10-2',1,'type','regex','email','completed','detect-and-mask',NULL,1,1,1,950,950,950,'','',0,0,0,0,0,'',1767312000000),
 ('ui-f3b10-2',2,'layer','ner','','completed','detect-and-mask',35,0,0,0,0,0,0,'','',0,0,0,0,0,'',1767312000000),
 ('ui-f3b10-2',3,'consensus','','','','',NULL,0,0,0,0,0,0,'most-restrictive','',2,1,1,0,0,'',1767312000000),
 ('ui-f3b10-3',0,'layer','regex','','completed','detect-and-mask',0,0,0,0,0,0,0,'','',0,0,0,0,0,'',1767312060000),
 ('ui-f3b10-3',1,'layer','ner','','unavailable','detect-and-mask',NULL,0,0,0,0,0,0,'','',0,0,0,0,0,'',1767312060000),
 ('ui-f3b10-3',2,'consensus','','','','',NULL,0,0,0,0,0,0,'most-restrictive','',1,0,0,0,0,'',1767312060000);
