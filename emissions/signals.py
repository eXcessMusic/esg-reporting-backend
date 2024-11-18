from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

'''
This file contains signal handlers for the emissions app.
Signals allow certain senders to notify a set of receivers that some action has taken place.
They're especially useful for decoupling applications and maintaining data integrity.
'''

@receiver(post_save, sender='emissions.Source')
def update_report_emissions(sender, instance, **kwargs):
    '''
    Signal handler to update report emissions when a Source is saved.

    This function is called automatically after a Source instance is saved.
    It ensures that the total emissions for the associated Report are recalculated.

    :param sender: The model class that sent the signal (Source in this case)
    :param instance: The actual instance of the Source that was saved
    :param kwargs: Additional keyword arguments
    '''
    # Call the update_total_emissions method on the report associated with this source
    instance.report.update_total_emissions()

@receiver(post_delete, sender='emissions.Source')
def update_report_emissions_on_delete(sender, instance, **kwargs):
    '''
    Signal handler to update report emissions when a Source is deleted.

    This function is called automatically after a Source instance is deleted.
    It ensures that the total emissions for the associated Report are recalculated.

    :param sender: The model class that sent the signal (Source in this case)
    :param instance: The actual instance of the Source that was deleted
    :param kwargs: Additional keyword arguments
    '''
    # Call the update_total_emissions method on the report associated with this source
    instance.report.update_total_emissions()

'''
Note: These signals help maintain data consistency by automatically updating
the total emissions of a Report whenever a Source is added, modified, or deleted.
This way, we don't have to remember to manually update the Report's emissions
every time we make changes to its Sources.
'''