import discord
from discord.ext import commands
from typing import Optional
from discord import app_commands
from discord.ui import Button
from modals.constants import tmw_id, timezones

from typing import Optional
#############################################################

options = []
for result in timezones:
    item = discord.SelectOption(label=f'{result}')
    options.append(item)

#############################################################

class Save_screen(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 900, selection):
        super().__init__(timeout=timeout)
        self.selection = selection
        
    @discord.ui.button(label='Save', style=discord.ButtonStyle.green, row=1)
    async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button, disable=False):
        myembed = await self.edit_embed(self.data)
        await interaction.response.edit_message(embed=myembed)
        
    @discord.ui.button(label='Back', style=discord.ButtonStyle.gray, row=1, disabled=True)
    async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        ...

class Select_Screen(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 900, data):
        super().__init__(timeout=timeout)
    
    @discord.ui.select(min_values = 1, max_values = 1, options=options)
    async def select_channels(self, interaction: discord.Interaction, select: str):
        return await interaction.response.edit_message(view=Save_screen(selection=select), embed=await Save_screen(interaction, select))
        
    async def save_screen(self, interaction: discord.Interaction, selection: str):
        myembed = discord.Embed(title="Settings saved", description="This message will auto delete itself shortly.")
        myembed.add_field(name="Current timezone", value=selection if selection else "n/a")
        myembed.set_footer(text="Pick an index to retrieve a scene next.")

        return myembed

    @discord.ui.button(label='Save', style=discord.ButtonStyle.green, row=1, disabled=True)
    async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        ...
        
    @discord.ui.button(label='Quit', style=discord.ButtonStyle.red, row=1, disabled=False)
    async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        return await interaction.delete_original_response()
        
# class Start_screen(discord.ui.View):
#     def __init__(self, *, timeout: float | None = 180):
#         super().__init__(timeout=timeout)
        
        
#     @discord.ui.button(label='Next', style=discord.ButtonStyle.gray, row=1, disabled=False)
#     async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         return await interaction.response.edit_message(embed=)
    
#     @discord.ui.button(label='Quit', style=discord.ButtonStyle.red, row=1, disabled=False)
#     async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
#         return await interaction.delete_original_response()

class MyView(discord.ui.View):
    def __init__(self, *, timeout: Optional[float] = 900, data):
        super().__init__(timeout=timeout)
        self.timezones: list = data
        #self.page = 0
        self.save = Button(label='Save', style=discord.ButtonStyle.green, row=1)
        self.timezone_selection = ""
        #self.appearance_selection = ""

    async def start_screen(self, interaction):
        #self.add_item(Button(label='Back', style=discord.ButtonStyle.gray, row=1, disabled=True, custom_id="back_button"))
        self.add_item(Button(label='Next', style=discord.ButtonStyle.blurple, row=1, custom_id='next_button'))

    @discord.ui.select(min_values = 1, max_values = 1, options=options)
    async def select_channels(self, interaction: discord.Interaction, select: str):
    
        self.add_item(self.save)
        self.save.callback = self.save_btn_callback(self.save, interaction)
        return await interaction.response.edit_message(embed=await self.start_screen(interaction, select.values[0]), view=self)

    async def save_btn_callback(self, button, interaction):
        print(button)
    # async def on_next_button_click(self, interaction: discord.Interaction):
    #     # Disable the button upon click
    #     for item in self.children:
    #         if isinstance(item, discord.ui.Button):
    #             if (item.custom_id == "next_button"):
    #                 if self.page == 0:
    #                     self.page = 1
    #                     self.remove_item(item)
    #                     self.add_item(Button(label='Save', style=discord.ButtonStyle.green, row=1, disabled=True, custom_id="save_button"))
    #                     select = Select(min_values = 1, max_values = 1, options=options)

    #                     async def my_callback(interaction):
    #                         self.timezone_selection = select.values[0]
    #                         for item in self.children:
    #                             if isinstance(item, discord.ui.Button):
    #                                 if (item.custom_id == "save_button"):
    #                                     item.disabled = False
    #                         await interaction.response.edit_message(view=self, embed=await self.timezone_embed(interaction, self.timezone_selection))
                            
                        
    #                     select.callback = my_callback
    #                     self.add_item(select)
    #                     await interaction.response.edit_message(view=self, embed=await self.timezone_embed(interaction, self.timezone_selection))


                # if (item.custom_id == "back_button"):
                #     item.disabled = False
                #     if (self.page != 0):
                #         item.disabled = False
                        # if (self.page == 1):
                        #     myembed = discord.Embed(title=f'Immersion logging setup (ILS)',description=f'Individualize your logging experience by changing your timezone.')
                        #     myembed.add_field(name='Timezone', value='n/a')
                        #     item.disabled = True
                        #     await interaction.response.edit_message(view=self, embed=myembed)

                # if (item.custom_id == "save_button"):
                #     for item in self.children:
                #             self.remove_item(item)
                #     await interaction.response.edit_message(view=self, embed=await self.save_screen(interaction, self.timezone_selection))


    # async def save_screen(self, interaction: discord.Interaction, selection: str):
    #     myembed = discord.Embed(title="Settings saved", description="This message will auto delete itself shortly.")
    #     myembed.add_field(name="Current timezone", value=selection if selection else "n/a")
    #     myembed.set_footer(text="Pick an index to retrieve a scene next.")

    #     return myembed

    async def start_screen(self, interaction: discord.Interaction, selection: str):
        myembed = discord.Embed(title=f'Select your timezone',description=f'''Individualize your logging experience by changing your timezone.
                                Selecting your timezone is required to log your immersion. After selecting your timezone, you can change it one more time.
                                If you do wish to change your timezone for another time, ping Timm.''')
        myembed.add_field(name='Current timezone', value='n/a')
        myembed.add_field(name='Selected timezone', value=selection if selection else "n/a")

        return myembed

    # def add_item(self, item):
    #     # Override add_item to handle custom_id assignment and automatic handling
    #     if isinstance(item, Button):
    #         item.callback = self.on_next_button_click
    #     super().add_item(item)
        
    # async def select_callback(self, interaction: discord.Interaction):
    #     relevant_result = Select.values[0]
    #     print(relevant_result)

    # async def appearance_embed(self, interaction: discord.Interaction, selection: str):
    #     myembed = discord.Embed(title="Appearance settings", description="Select the features your log messages should display to you,")
    #     myembed.add_field(name="Currently", value=selection if selection else "n/a")
    #     #myembed.add_field(inline=False, name="Explanation", value="Goals you set yourself end at the end of a day or at a specifc date you set. To adjust for timezone differences, you can select your timezone so it will be more comfortable hitting your goal.")
    #     myembed.set_footer(text="Pick an index to retrieve a scene next.")

    #     return myembed

    async def timezone_embed(self, interaction: discord.Interaction, selection: str):
        self.page = 1
        myembed = discord.Embed(title="Timezone settings", description="Select a timezone from the dropdown menu below. This is necessary for being able to set yourself goals within the bot.")
        myembed.add_field(name="Currently", value=selection if selection else "n/a")
        myembed.add_field(inline=False, name="Explanation", value="Goals you set yourself end at the end of a day or at a specifc date you set. To adjust for timezone differences, you can select your timezone so it will be more comfortable hitting your goal.")
        myembed.set_footer(text="Pick an index to retrieve a scene next.")

        return myembed

    # @discord.ui.button(label='Quit', style=discord.ButtonStyle.red, row=1, custom_id="quit")
    # async def stop_pages(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.delete_original_response()
        
    # @discord.ui.button(label='Back', style=discord.ButtonStyle.gray, row=1, disabled=True, custom_id="Back")
    # async def go_to_previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     if self.page == 0:
    #         button.disabled = True
    #         button._refresh_component(button=button)
    #     elif self.page == 1:
    #         button.disabled = False
    #         button.style = discord.ButtonStyle.blurple
    #         button._refresh_component(button=button)

    #         myembed = await self.edit_embed(self.data)
    #         await interaction.response.edit_message(embed=myembed)
    
    
    # @discord.ui.button(label='Next', style=discord.ButtonStyle.gray, row=1)
    # async def go_to_next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     myembed = await self.edit_embed(self.data)
    #     await interaction.response.edit_message(embed=myembed)

# class TimeZone(NamedTuple):
#     label: str
#     key: str

#     @classmethod
#     async def convert(cls, argument: str):
#         # Prioritise aliases because they handle short codes slightly better
#         if argument in timezones:
#             return cls(key=timezones[argument], label=argument)

#     def to_choice(self) -> app_commands.Choice[str]:
#         return app_commands.Choice(name=self.label, value=self.key)

class Setup(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.myguild = self.bot.get_guild(tmw_id)

    @app_commands.command(name='setup', description=f'Setup your immersion experience.')
    @app_commands.checks.has_role("Moderator")
    async def setup(self, interaction: discord.Interaction):

        # channel = interaction.channel
        # if channel.id != 1010323632750350437 and channel.id != 814947177608118273 and channel.type != discord.ChannelType.private:
        #     return await interaction.response.send_message(content='You can only log in #immersion-log or DMs.',ephemeral=True)
        
        myembed = discord.Embed(title=f'Select your timezone',description=f'''Individualize your logging experience by changing your timezone.
                                Selecting your timezone is required to log your immersion. After selecting your timezone, you can change it one more time.
                                If you do wish to change your timezone for another time, ping Timm.''')
        myembed.add_field(name='Current timezone', value='n/a')
        myembed.add_field(name='Selected timezone', value='n/a')
    
        options = []
        for result in timezones:
            item = discord.SelectOption(label=f'{result}')
            options.append(item)
            
        view = Select_Screen(data=options)
        
        # await view.start_screen(interaction)
        
        await interaction.response.send_message(embed=myembed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Setup(bot))