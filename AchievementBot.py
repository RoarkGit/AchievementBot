import base64
import hashlib
import pyxivapi
import shelve

from discord.ext import commands
from discord.utils import get


ACHIEVEMENTS_ROLE_MAP = {
    2476: 794964126140465222
}
CHARACTER_DB_FILENAME = 'characters.db'
LODESTONE_URL = 'https://na.finalfantasyxiv.com/lodestone/character/{id}/'

bot = commands.Bot(command_prefix='.', help_command=None)
characters = shelve.open(CHARACTER_DB_FILENAME, writeback=True)
xivapi = pyxivapi.XIVAPIClient(api_key='')

@bot.event
async def on_ready():
    print('Connected and loaded states of {numUsers} users.'.format(
        numUsers=len(characters)))
    
@bot.command()
async def help(ctx):
    response = '```'
    response += ('.register world first last\n'
                 '\tgoes through registration workflow to verify your character'
                 ' is actually yours\n'
                 '\tExample: .register zalera liam galt\n')
    response += ('.grant\n'
                 '\tgrants achievement-based roles based on registered '
                 'characters\' completed achievements\n'
                 '\tnote: requires achievements to be public when executed')
    response += '```'
    await ctx.send(response)

@bot.command()
async def register(ctx, world, first, last):
    characterId = await characterToId(world, first, last)
    authorId = str(ctx.author.id)
    if characterId:
        if authorId not in characters:
            characters[authorId] = []
        if characterId in characters[authorId]:
            response = 'You\'ve already registered that character!'
        else:
            # Set to unverified to start
            character = await xivapi.character_by_id(lodestone_id=characterId)
            bio = character['Character']['Bio']
            challenge = generateChallenge(world, first, last, characterId)
            if challenge in bio:
                response = ('Registration successful! You can remove the '
                            'challenge from your profile now.')
                characters[authorId].append(characterId)
            else:
                response = ('I found this character! ' + 
                    LODESTONE_URL.format(id=characterId) + '\n' +
                    'Please update your character profile to include this: \n' +
                    '```' + challenge + '```\n' +
                    'Once finished, run `.register` again to complete '
                    'registration of your character.')
    else:
        response = ('I was not able to find that character. Double check your '
                    'spelling and formatting!')
    await ctx.send(response)

@bot.command()
async def grant(ctx):
    authorId = str(ctx.author.id)
    if authorId not in characters or not characters[authorId]:
        response = 'You haven\'t registered any characters yet!'
    else:
        for characterId in characters[authorId]:
            character = await xivapi.character_by_id(
                lodestone_id=characterId,
                include_achievements=True
            )

            if not character['AchievementsPublic']:
                continue

            for achievement in character['Achievements']['List']:
                if achievement['ID'] in ACHIEVEMENTS_ROLE_MAP:
                    role = get(ctx.guild.roles,
                               id=ACHIEVEMENTS_ROLE_MAP[achievement['ID']])
                    await ctx.author.add_roles(role)
        response = 'Updated roles to reflect achievement status!'

    await ctx.send(response)

async def characterToId(world, first, last):
    name = first + ' ' + last
    character = await xivapi.character_search(
        world=world,
        forename=first,
        surname=last
    )

    print('Finding matching character...')
    while character['Pagination']['Page'] != 0:
        for c in character['Results']:
            print(c['Name'], c['ID'])
            if c['Name'].lower() == name.lower():
                return str(c['ID'])
        character = await xivapi.character_search(
            world=world,
            forename=first,
            surname=last,
            page=character['Pagination']['Page'] + 1
        )

    return None

def generateChallenge(world, first, last, id):
    return (base64.b64encode(
        hashlib.sha1((world + first + last + id).lower().encode()).digest())
        .decode())

if __name__ == '__main__':
    bot.run('')