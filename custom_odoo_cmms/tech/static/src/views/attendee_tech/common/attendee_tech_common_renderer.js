/** @odoo-module **/

import { TechCommonRenderer } from "@web/views/tech/tech_common/tech_common_renderer";
import { AttendeeTechCommonPopover } from "@tech/views/attendee_tech/common/attendee_tech_common_popover";

export class AttendeeTechCommonRenderer extends TechCommonRenderer {
    /**
     * @override
     *
     * Give a new key to our fc records to be able to iterate through in templates
     */
    convertRecordToEvent(record) {
        return {
            ...super.convertRecordToEvent(record),
            id: record._recordId || record.id,
        };
    }

    /**
     * @override
     */
    onEventRender(info) {
        super.onEventRender(...arguments);
        const { el, event } = info;
        const record = this.props.model.records[event.id];

        if (record) {
            if (record.rawRecord.is_highlighted) {
                el.classList.add("o_event_highlight");
            }
            if (record.isAlone) {
                el.classList.add("o_attendee_status_alone");
            } else {
                el.classList.add(`o_attendee_status_${record.attendeeStatus}`);
            }
        }
    }

    /**
     * @override
     *
     * Allow slots to be selected over multiple days
     */
    isSelectionAllowed(event) {
        return true;
    }
}
AttendeeTechCommonRenderer.eventTemplate = "tech.AttendeeTechCommonRenderer.event";
AttendeeTechCommonRenderer.components = {
    ...TechCommonRenderer.components,
    Popover: AttendeeTechCommonPopover,
};
