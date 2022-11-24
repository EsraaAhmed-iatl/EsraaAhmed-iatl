from odoo import fields, models, api


class WorkshopPerformanceReport(models.TransientModel):
    _name = 'workshop.performance'

    from_date = fields.Date(string='Date From', required=True, default=lambda self: fields.Date.today())
    to_date = fields.Date(string='Date To', required=True)

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        data['job'] = self.env.context.get('active_ids', [])
        jobs = self.env['job.order'].browse(data['job'])
        datas = {
            'ids': [],
            'model': 'job.order',
            'form': data,
            # 'start_date': self.from_date,
            # 'end_date': self.to_date,
        }
        return self.env.ref('ii_service_15.action_workshop_performance_report').report_action(jobs, data=datas)

class WorkshopReport(models.AbstractModel):
    _name ='report.ii_service_15.report_workshop_performance'

    def get_values(self, form):
        value = []
        main_records = self.env['job.order'].search([])
        for main_record in main_records:
            print("YYYYYYYYYYyy", main_record)
            value.append(main_record)

        return value

    @api.model
    def _get_report_values(self, docids, data=None):
        # docs = self.env['job.order'].browse(docids)
        # docs = self.env['job.order'].browse(data['context']['active_ids'])
        docs = self.get_values(data['form'])
        print("***********************", docs)
        return {
            'doc_ids': docids,
            'doc_model': 'job.order',
            'docs': docs,
            'data': data,
        }
