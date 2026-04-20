# Generated data migration to create RSPC test users and roles

from django.db import migrations

def create_test_users_and_roles(apps, schema_editor):
    """Create test users and assign RSPC roles."""
    # Get models from correct apps
    User = apps.get_model('auth', 'User')
    Designation = apps.get_model('globals', 'Designation')  # From globals app!
    HoldsDesignation = apps.get_model('globals', 'HoldsDesignation')  # Also from globals app!
    
    # Create designations
    des_pi, _ = Designation.objects.get_or_create(name='faculty_pi')
    des_hod, _ = Designation.objects.get_or_create(name='hod')
    des_dean, _ = Designation.objects.get_or_create(name='dean_rspc')
    des_director, _ = Designation.objects.get_or_create(name='director')
    des_admin, _ = Designation.objects.get_or_create(name='rspc_admin')
    des_committee, _ = Designation.objects.get_or_create(name='committee')
    
    # Create test users
    test_users = [
        ('pi_user', 'PI', 'User', 'pi_user@fusion.edu.in'),
        ('hod_user', 'HOD', 'User', 'hod_user@fusion.edu.in'),
        ('dean_user', 'Dean', 'User', 'dean_user@fusion.edu.in'),
        ('director_user', 'Director', 'User', 'director_user@fusion.edu.in'),
        ('admin_user', 'Admin', 'User', 'admin_user@fusion.edu.in'),
        ('committee_user', 'Committee', 'User', 'committee_user@fusion.edu.in'),
    ]
    
    created_users = []
    for username, first_name, last_name, email in test_users:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'email': email
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        created_users.append(user)
    
    # Assign roles via HoldsDesignation
    role_mapping = [
        ('pi_user', des_pi),
        ('hod_user', des_hod),
        ('dean_user', des_dean),
        ('director_user', des_director),
        ('admin_user', des_admin),
        ('committee_user', des_committee),
    ]
    
    for username, designation in role_mapping:
        user = User.objects.get(username=username)
        HoldsDesignation.objects.get_or_create(
            user=user,
            designation=designation,
            defaults={'working': user}
        )


def reverse_create_test_users(apps, schema_editor):
    """Reverse: Delete test users and roles (optional)."""
    HoldsDesignation = apps.get_model('research_procedures', 'HoldsDesignation')
    
    # Remove test user role assignments
    test_usernames = ['pi_user', 'hod_user', 'dean_user', 'director_user', 'admin_user', 'committee_user']
    for username in test_usernames:
        HoldsDesignation.objects.filter(user__username=username).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('research_procedures', '0010_gap_items_uc021_uc022_uc023_br020'),
        ('globals', '0001_initial'),  # Ensure Designation model exists
    ]

    operations = [
        migrations.RunPython(create_test_users_and_roles, reverse_create_test_users),
    ]
