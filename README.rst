SparNord
########

python-sparnord er et værktøj, der giver dig programmatisk adgang til Spar Nords netbank.
I al sin gribende enkelhed lader det dig hive dine kontoudtog ud.

Det er ganske enkelt at bruge:

    >>> import sparnord
    >>> sn = sparnord.SparNord(username='nemidbrugernavn', password='nemidpassword')
    >>> sn.get_accounts()
    [{'accountnr': u'246123456',
      'currency': u'DKK',
      'name': u'Spar Nord Stjernekonto',
      'regnr': u'9314'},
     {'accountnr': u'4566474882',
      'currency': u'DKK',
      'name': u'Opsparing',
      'regnr': u'9314'}]
    >>> print sn.get_account_info_csv('246123456')
    "23-12-2013";"23-12-2013";"Salling Stormagasi";"-175,00";"1.953,03"
    "23-12-2013";"23-12-2013";"SuperBest Skalborg";"-773,73";"2.128,03"
    "23-12-2013";"23-12-2013";"Netto Skelagervej";"-689,90";"2.901,76"

Hvis du har flere aftaler (hvis du eksempelvis også har en erhvervskonto), så skal du også sørge for at angive aftalenummeret:

    >>> sn = sparnord.SparNord(username='nemidbrugernavn', password='nemidpassword')
    >>> sn.get_accounts()
    Exception: AgreementIdRequired: You must set the agreement ID to go to the accounts overview page
	>>> sn.get_agreements()
    Exception: MultipleUserAccountsException: Multiple user accounts were shown, but no ID was given: [[u'92412354524', u'931491235455524', u'Min kones Navn'], [u'90412345607', u'931461234561913', u'Linux2go'], [u'90412345607', u'901234512345628', u'S\xf8ren Lerfors Hansen']]
	>>> sn.user_id = '90412345607'
	>>> sn.get_agreements()
    ['931461234561913', '901234512345628']
	>>> sn.agreement_id = '901234512345628'
	>>> sn.get_accounts()
    [{'accountnr': u'246123456',
      'currency': u'DKK',
      'name': u'Spar Nord Stjernekonto',
      'regnr': u'9314'},
     {'accountnr': u'4566474882',
      'currency': u'DKK',
      'name': u'Opsparing',
      'regnr': u'9314'}]

etc.


